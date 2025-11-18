# Ultimate Duplicate Cleaner

Fast and safe duplicate file finder and remover for Windows, designed for R36S handhelds and other retro gaming devices.

## 🎮 Perfect for R36S & Retro Gaming Devices

This tool was specifically created to clean up bloated SD cards on R36S handheld consoles and similar retro gaming devices. It's common to have duplicate ROM files scattered across different folders - this script finds and removes them safely.

## ✨ Features

- **Lightning Fast**: Multi-threaded scanning using all CPU cores (16 workers on typical systems)
- **100% Accurate**: Three-phase detection algorithm (size → quick hash → full hash)
- **Safe Deletion**: Moves files to Recycle Bin instead of permanent deletion
- **Smart Logic**: Always keeps the OLDEST file (original) and deletes NEWER files (copies)
- **Detailed Reporting**: Shows statistics and generates detailed log before deletion
- **User Confirmation**: Always asks before deleting anything
- **Progress Bars**: Visual progress indication for all operations
- **No Dependencies Required**: Works with standard Python, optional modules for better experience

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Windows (for Recycle Bin support)

### Optional Dependencies (Recommended)

```bash
pip install send2trash tqdm
```

- `send2trash` - Enables Recycle Bin deletion (without it, files are permanently deleted!)
- `tqdm` - Shows nice progress bars

### Usage

1. Run the script:
```bash
python duplicate_cleaner.py
```

2. Select drive (for R36S, typically the SD card drive)

3. Wait for scan to complete (shows progress for each phase)

4. Review statistics and check the log file

5. Confirm deletion when prompted

## 📊 How It Works

### Three-Phase Algorithm

1. **Phase 1: Size Grouping**
   - Indexes all files by size
   - Only files with matching sizes are candidates

2. **Phase 2: Quick Hash**
   - MD5 hash of first 8KB for fast comparison
   - Runs in parallel using all CPU cores
   - Reduces candidates by ~50%

3. **Phase 3: Full Hash**
   - Complete MD5 hash of remaining candidates
   - Final verification of 100% duplicates

### Keep vs Delete Logic

- **KEEP**: File with the oldest modification date (original)
- **DELETE**: All files with newer modification dates (copies)

## 🎯 Real-World Results

### Example: R36S Stock SD Card (F:\ drive)
- Scanned: 45,087 files (40.34 GB)
- Found: 5,617 duplicate groups
- Deleted: 11,551 files
- Freed: 1.86 GB

### Example: Data folder cleanup
- Scanned: Various files
- Deleted: 1,516 duplicates
- Freed: 1.98 GB

## 📝 Output Files

- `duplicate_log.txt` - Detailed report of all duplicate groups, what will be kept, and what will be deleted

## ⚙️ Configuration

The script automatically skips these folders:
- `$RECYCLE.BIN`
- `System Volume Information`
- `themes`

You can modify the `skip_patterns` set in the code if you want to exclude additional folders.

## 🔒 Safety Features

1. **Recycle Bin**: Files go to Recycle Bin (if `send2trash` installed), not permanently deleted
2. **Confirmation Required**: Always prompts before deletion
3. **Detailed Log**: Review exactly what will be deleted before confirming
4. **Keeps Originals**: Logic ensures oldest file (original) is always preserved

## ⚠️ Important Notes

- **Without send2trash**: Files will be PERMANENTLY deleted (cannot be recovered)
- **Always review the log** before confirming deletion
- **Backup important data** before running on critical drives
- The script uses modification date to determine age (older date = original)

## 🐛 Troubleshooting

### Script runs slow
- Install multiprocessing support (should be included in standard Python)
- Close other applications to free up CPU

### Progress bar stuck
- Make sure you have the latest version of the script
- Try reinstalling tqdm: `pip install --upgrade tqdm`

### Files not going to Recycle Bin
- Install send2trash: `pip install send2trash`
- Without it, files are permanently deleted!

## 📄 License

Free to use and modify. Created for the retro gaming community.

## 🤝 Contributing

Found a bug or have a suggestion? Feel free to open an issue or submit a pull request!

---

**Made with ❤️ for the R36S and retro gaming community**
