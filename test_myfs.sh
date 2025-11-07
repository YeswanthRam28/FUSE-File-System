#!/bin/bash

# FUSE filesystem mount point
MOUNT_DIR="/tmp/myfs_mount"

# Check if the filesystem binary exists
if [ ! -f ./myfs ]; then
    echo "Error: myfs executable not found. Compile first with gcc myfs.c -o myfs \`pkg-config fuse3 --cflags --libs\`"
    exit 1
fi

# Create mount point
mkdir -p $MOUNT_DIR

# Run the filesystem in background
./myfs $MOUNT_DIR &
FS_PID=$!
sleep 1  # wait for mount

echo "Mounted FUSE filesystem at $MOUNT_DIR"

# List root directory
echo "Root directory contents:"
ls $MOUNT_DIR
echo

# Test static files
echo "Reading static files..."
for file in hello info.txt time.txt; do
    echo "Contents of $file:"
    cat "$MOUNT_DIR/$file"
    echo
done

# Test notes directory
NOTES_DIR="$MOUNT_DIR/notes"
echo "Creating /notes directory and files..."
mkdir -p "$NOTES_DIR" 2>/dev/null

# Create and write notes
echo "This is note 1" > "$NOTES_DIR/note1.txt"
echo "This is note 2" > "$NOTES_DIR/note2.txt"

# Append to note1
echo "Appending to note1" >> "$NOTES_DIR/note1.txt"

# Read notes
echo "Reading notes:"
for note in note1.txt note2.txt; do
    echo "Contents of $note:"
    cat "$NOTES_DIR/$note"
    echo
done

# List notes
echo "Listing /notes directory:"
ls "$NOTES_DIR"
echo

# Test overwrite beyond MAX_FILE_SIZE (optional)
# echo "Testing write limit..."
# dd if=/dev/zero bs=1024 count=2 | tr '\0' 'A' > "$NOTES_DIR/large_note.txt"



echo "Test completed!"
