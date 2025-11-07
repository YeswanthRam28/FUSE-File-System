#define FUSE_USE_VERSION 35
#include <fuse3/fuse.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <time.h>
#include <stdlib.h>

#define MAX_FILES 100
#define MAX_FILE_SIZE 1024

// --- Static files ---
static const char *hello_path = "/hello";
static const char *hello_str  = "Hello FUSE World!\n";

static const char *info_path  = "/info.txt";
static const char *info_str   = "This is our FUSE project.\n";

static const char *time_path  = "/time.txt";
static const char *log_path   = "/log.txt";
static const char *secure_dir = "/secure";

// --- In-memory file structure ---
struct mem_file {
    char name[64];
    char content[MAX_FILE_SIZE];
    size_t size;
    int encrypted; // 0 = normal, 1 = secure
};

static struct mem_file notes[MAX_FILES];
static int note_count = 0;

// --- Logging buffer ---
static char log_content[MAX_FILE_SIZE * 2];
static size_t log_size = 0;

// --- Helper: logging ---
static void add_log(const char *action, const char *path) {
    time_t t = time(NULL);
    char entry[256];
    snprintf(entry, sizeof(entry), "[%s] %s -> %s\n", strtok(ctime(&t), "\n"), action, path);
    size_t len = strlen(entry);
    if (log_size + len < sizeof(log_content)) {
        memcpy(log_content + log_size, entry, len);
        log_size += len;
    }
}

// --- Helper: find file ---
static struct mem_file* get_note(const char *path) {
    for (int i = 0; i < note_count; i++) {
        char fullpath[128];
        if (notes[i].encrypted)
            snprintf(fullpath, sizeof(fullpath), "/secure/%s", notes[i].name);
        else
            snprintf(fullpath, sizeof(fullpath), "/notes/%s", notes[i].name);
        if (strcmp(path, fullpath) == 0)
            return &notes[i];
    }
    return NULL;
}

// --- Helper: XOR encryption ---
static void xor_cipher(char *data, size_t size) {
    const char key = 0xAA; // simple XOR key
    for (size_t i = 0; i < size; i++) {
        data[i] ^= key;
    }
}

// --- getattr ---
static int myfs_getattr(const char *path, struct stat *stbuf, struct fuse_file_info *fi) {
    (void) fi;
    memset(stbuf, 0, sizeof(struct stat));

    if (strcmp(path, "/") == 0) {
        stbuf->st_mode = S_IFDIR | 0755;
        stbuf->st_nlink = 2;
        return 0;
    } else if (strcmp(path, hello_path) == 0) {
        stbuf->st_mode = S_IFREG | 0444;
        stbuf->st_nlink = 1;
        stbuf->st_size = strlen(hello_str);
        return 0;
    } else if (strcmp(path, info_path) == 0) {
        stbuf->st_mode = S_IFREG | 0444;
        stbuf->st_nlink = 1;
        stbuf->st_size = strlen(info_str);
        return 0;
    } else if (strcmp(path, time_path) == 0) {
        stbuf->st_mode = S_IFREG | 0444;
        stbuf->st_nlink = 1;
        stbuf->st_size = 64;
        return 0;
    } else if (strcmp(path, log_path) == 0) {
        stbuf->st_mode = S_IFREG | 0444;
        stbuf->st_nlink = 1;
        stbuf->st_size = log_size;
        return 0;
    } else if (strcmp(path, "/notes") == 0 || strcmp(path, secure_dir) == 0) {
        stbuf->st_mode = S_IFDIR | 0755;
        stbuf->st_nlink = 2 + note_count;
        return 0;
    } else {
        struct mem_file* nf = get_note(path);
        if (nf) {
            stbuf->st_mode = S_IFREG | 0666;
            stbuf->st_nlink = 1;
            stbuf->st_size = nf->size;
            return 0;
        }
    }

    return -ENOENT;
}

// --- readdir ---
static int myfs_readdir(const char *path, void *buf, fuse_fill_dir_t filler,
                        off_t offset, struct fuse_file_info *fi,
                        enum fuse_readdir_flags flags) {
    (void) offset; (void) fi; (void) flags;

    if (strcmp(path, "/") == 0) {
        filler(buf, ".", NULL, 0, 0);
        filler(buf, "..", NULL, 0, 0);
        filler(buf, hello_path+1, NULL, 0, 0);
        filler(buf, info_path+1, NULL, 0, 0);
        filler(buf, time_path+1, NULL, 0, 0);
        filler(buf, log_path+1, NULL, 0, 0);
        filler(buf, "notes", NULL, 0, 0);
        filler(buf, "secure", NULL, 0, 0);
        return 0;
    } else if (strcmp(path, "/notes") == 0 || strcmp(path, secure_dir) == 0) {
        filler(buf, ".", NULL, 0, 0);
        filler(buf, "..", NULL, 0, 0);
        for (int i = 0; i < note_count; i++) {
            if ((strcmp(path, "/notes") == 0 && !notes[i].encrypted) ||
                (strcmp(path, secure_dir) == 0 && notes[i].encrypted)) {
                filler(buf, notes[i].name, NULL, 0, 0);
            }
        }
        return 0;
    }

    return -ENOENT;
}

// --- open ---
static int myfs_open(const char *path, struct fuse_file_info *fi) {
    add_log("OPEN", path);
    return 0;
}

// --- read ---
static int myfs_read(const char *path, char *buf, size_t size,
                     off_t offset, struct fuse_file_info *fi) {
    (void) fi;
    char time_buf[64];
    const char *content = NULL;
    size_t len = 0;

    if (strcmp(path, hello_path) == 0) {
        content = hello_str;
        len = strlen(content);
    } else if (strcmp(path, info_path) == 0) {
        content = info_str;
        len = strlen(content);
    } else if (strcmp(path, time_path) == 0) {
        time_t t = time(NULL);
        snprintf(time_buf, sizeof(time_buf), "Current time: %s", ctime(&t));
        content = time_buf;
        len = strlen(content);
    } else if (strcmp(path, log_path) == 0) {
        content = log_content;
        len = log_size;
    } else {
        struct mem_file* nf = get_note(path);
        if (!nf) return -ENOENT;

        if (nf->encrypted) {
            char tmp[MAX_FILE_SIZE];
            memcpy(tmp, nf->content, nf->size);
            xor_cipher(tmp, nf->size);
            content = tmp;
            len = nf->size;
            if (offset < len) {
                if (offset + size > len)
                    size = len - offset;
                memcpy(buf, tmp + offset, size);
                add_log("READ", path);
                return size;
            }
            return 0;
        } else {
            content = nf->content;
            len = nf->size;
        }
    }

    if (offset >= len)
        return 0;

    if (offset + size > len)
        size = len - offset;

    memcpy(buf, content + offset, size);
    add_log("READ", path);
    return size;
}

// --- write ---
static int myfs_write(const char *path, const char *buf, size_t size,
                      off_t offset, struct fuse_file_info *fi) {
    (void) fi;
    struct mem_file* nf = get_note(path);
    if (!nf) return -ENOENT;

    if (offset + size > MAX_FILE_SIZE)
        size = MAX_FILE_SIZE - offset;

    memcpy(nf->content + offset, buf, size);
    nf->size = offset + size;

    if (nf->encrypted) xor_cipher(nf->content, nf->size);

    add_log("WRITE", path);
    return size;
}

// --- create ---
static int myfs_create(const char *path, mode_t mode, struct fuse_file_info *fi) {
    (void) mode; (void) fi;

    if (note_count >= MAX_FILES)
        return -ENOSPC;

    if (get_note(path)) return -EEXIST;

    struct mem_file* nf = &notes[note_count++];
    memset(nf, 0, sizeof(*nf));

    if (strncmp(path, "/notes/", 7) == 0) {
        strncpy(nf->name, path+7, sizeof(nf->name)-1);
        nf->encrypted = 0;
    } else if (strncmp(path, "/secure/", 8) == 0) {
        strncpy(nf->name, path+8, sizeof(nf->name)-1);
        nf->encrypted = 1;
    } else {
        return -EACCES;
    }

    add_log("CREATE", path);
    return 0;
}

// --- unlink (delete) ---
static int myfs_unlink(const char *path) {
    for (int i = 0; i < note_count; i++) {
        char fullpath[128];
        if (notes[i].encrypted)
            snprintf(fullpath, sizeof(fullpath), "/secure/%s", notes[i].name);
        else
            snprintf(fullpath, sizeof(fullpath), "/notes/%s", notes[i].name);

        if (strcmp(path, fullpath) == 0) {
            for (int j = i; j < note_count-1; j++) {
                notes[j] = notes[j+1];
            }
            note_count--;
            add_log("DELETE", path);
            return 0;
        }
    }
    return -ENOENT;
}

// --- FUSE operations ---
static struct fuse_operations myfs_ops = {
    .getattr = myfs_getattr,
    .readdir = myfs_readdir,
    .open    = myfs_open,
    .read    = myfs_read,
    .write   = myfs_write,
    .create  = myfs_create,
    .unlink  = myfs_unlink,
};

int main(int argc, char *argv[]) {
    return fuse_main(argc, argv, &myfs_ops, NULL);
}
