#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ULTIMATE DUPLICATE CLEANER - All-in-One Solution

Workflow:
1. Scan for duplicates (fast, parallel)
2. Show statistics
3. Generate detailed log
4. Ask: Delete to Recycle Bin?
5. Delete if confirmed (safe, reversible)

Logic: Keep OLDEST file (original), delete NEWER files (copies)
"""

# Standard library imports (should always be available)
try:
    import os
    import sys
    import hashlib
    import time
    from pathlib import Path
    from collections import defaultdict
    from typing import Dict, List, Optional, Tuple
    from functools import partial
except ImportError as e:
    print(f"ERROR: Failed to import standard library: {e}")
    print("Your Python installation may be corrupted.")
    sys.exit(1)

# Multiprocessing (standard but check availability)
try:
    from multiprocessing import Pool, cpu_count
    MULTIPROCESSING_AVAILABLE = True
except ImportError:
    MULTIPROCESSING_AVAILABLE = False
    print("WARNING: multiprocessing not available")
    print("Will run in single-threaded mode (slower)\n")

# Optional: send2trash for Recycle Bin
try:
    from send2trash import send2trash
    TRASH_AVAILABLE = True
except ImportError:
    TRASH_AVAILABLE = False
    print("=" * 80)
    print("WARNING: 'send2trash' module not installed")
    print("=" * 80)
    print("Without this module, deleted files will be PERMANENTLY deleted!")
    print("Files will NOT go to Recycle Bin and CANNOT be recovered.")
    print()
    print("To install: pip install send2trash")
    print("=" * 80)
    print()

# Optional: tqdm for progress bars
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    # Silent - progress bars are nice to have but not critical

# Windows console
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

# Performance
BUFFER_SIZE = 262144  # 256KB
QUICK_HASH_SIZE = 8192  # 8KB


def calculate_quick_hash(file_path: Path) -> Optional[str]:
    """MD5 of first 8KB."""
    try:
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read(QUICK_HASH_SIZE)).hexdigest()
    except:
        return None


def calculate_full_hash(file_path: Path) -> Optional[str]:
    """Full MD5 hash."""
    md5 = hashlib.md5()
    try:
        with open(file_path, 'rb') as f:
            while chunk := f.read(BUFFER_SIZE):
                md5.update(chunk)
        return md5.hexdigest()
    except:
        return None


def hash_file_wrapper(file_path: Path, hash_type: str = 'full') -> Tuple[Path, Optional[str]]:
    """Wrapper for parallel hashing."""
    if hash_type == 'quick':
        return (file_path, calculate_quick_hash(file_path))
    return (file_path, calculate_full_hash(file_path))


def format_size(bytes: int) -> str:
    """Convert bytes to human-readable."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.2f} PB"


def get_file_age(file_path: Path) -> float:
    """Get modification timestamp."""
    try:
        return file_path.stat().st_mtime
    except:
        return float('inf')


def format_date(timestamp: float) -> str:
    """Format timestamp."""
    try:
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))
    except:
        return "Unknown"


def should_skip_directory(dir_path: str, skip_patterns: set) -> bool:
    """Check if directory should be skipped."""
    return os.path.basename(dir_path) in skip_patterns


def parallel_hash(func, items, workers, chunksize, desc="Progress"):
    """
    Hash files in parallel if multiprocessing available, with progress bar.
    Returns list of (path, hash) tuples.
    """
    if MULTIPROCESSING_AVAILABLE and workers > 1:
        with Pool(workers) as pool:
            iterator = pool.imap(func, items, chunksize=chunksize)
            if TQDM_AVAILABLE:
                return list(tqdm(iterator, total=len(items), desc=f"  {desc}", unit=" files"))
            else:
                return list(iterator)
    else:
        # Single-threaded fallback
        iterator = map(func, items)
        if TQDM_AVAILABLE:
            return list(tqdm(iterator, total=len(items), desc=f"  {desc}", unit=" files"))
        else:
            return list(iterator)


def find_duplicates(root_dir: str, skip_patterns: set, workers: int = None) -> Dict[str, List[Path]]:
    """
    Find duplicates using optimized algorithm.
    Returns: dict of hash -> file paths
    """
    if workers is None:
        workers = cpu_count() if MULTIPROCESSING_AVAILABLE else 1

    print(f"\n{'='*80}")
    print(f"SCANNING: {root_dir}")
    if MULTIPROCESSING_AVAILABLE:
        print(f"Workers: {workers} (CPU cores: {cpu_count()})")
    else:
        print(f"Mode: Single-threaded (multiprocessing unavailable)")
    print(f"{'='*80}\n")

    start_time = time.time()

    # Phase 1: Size grouping
    print("PHASE 1: Indexing files by size...")
    print("-" * 80)

    size_map: Dict[int, List[Path]] = defaultdict(list)
    total_files = 0
    total_size = 0

    for root, dirs, files in os.walk(root_dir):
        if should_skip_directory(root, skip_patterns):
            dirs.clear()
            continue

        for filename in files:
            file_path = Path(root) / filename
            try:
                file_size = file_path.stat().st_size
                size_map[file_size].append(file_path)
                total_files += 1
                total_size += file_size

                if total_files % 1000 == 0:
                    print(f"  {total_files:,} files | {format_size(total_size)}", end='\r')
            except:
                pass

    print(f"\n\n[OK] Indexed {total_files:,} files ({format_size(total_size)})")

    # Phase 2: Quick hash
    print(f"\nPHASE 2: Quick hash (8KB, parallel)...")
    print("-" * 80)

    candidates = [p for s, paths in size_map.items() if len(paths) > 1 for p in paths]

    if not candidates:
        print("\n[OK] No duplicates possible - all files have unique sizes")
        return {}

    print(f"  Hashing {len(candidates):,} files ({(len(candidates)/total_files)*100:.1f}% of total)...")

    quick_map: Dict[Tuple[int, str], List[Path]] = defaultdict(list)

    func = partial(hash_file_wrapper, hash_type='quick')
    results = parallel_hash(func, candidates, workers, chunksize=50, desc="Progress")

    for path, qhash in results:
        if qhash:
            quick_map[(path.stat().st_size, qhash)].append(path)

    print(f"\n[OK] Phase 2 complete")

    # Phase 3: Full hash
    print(f"\nPHASE 3: Full hash (complete files)...")
    print("-" * 80)

    final_candidates = [p for paths in quick_map.values() if len(paths) > 1 for p in paths]

    if not final_candidates:
        print("\n[OK] No duplicates found")
        return {}

    print(f"  Hashing {len(final_candidates):,} files...")

    hash_map: Dict[str, List[Path]] = defaultdict(list)

    func = partial(hash_file_wrapper, hash_type='full')
    results = parallel_hash(func, final_candidates, workers, chunksize=20, desc="Progress")

    for path, fhash in results:
        if fhash:
            hash_map[fhash].append(path)

    duplicates = {h: p for h, p in hash_map.items() if len(p) > 1}

    elapsed = time.time() - start_time
    print(f"\n{'='*80}")
    print(f"SCAN COMPLETE: {elapsed:.1f} seconds ({total_files/elapsed:.0f} files/sec)")
    print(f"{'='*80}\n")

    return duplicates


def analyze_duplicates(duplicates: Dict[str, List[Path]]) -> Tuple[List[Tuple[Path, Path, int]], Dict]:
    """
    Analyze duplicates and create deletion plan.
    Returns: (deletion_plan, statistics)
    """
    deletion_plan = []
    stats = {
        'groups': len(duplicates),
        'total_files': 0,
        'files_to_delete': 0,
        'files_to_keep': 0,
        'space_total': 0,
        'space_wasted': 0
    }

    for file_hash, file_paths in duplicates.items():
        # Sort by age (oldest first)
        sorted_by_age = sorted(file_paths, key=lambda p: get_file_age(p))

        oldest_file = sorted_by_age[0]  # Keep
        newer_files = sorted_by_age[1:]  # Delete

        file_size = oldest_file.stat().st_size

        stats['total_files'] += len(file_paths)
        stats['files_to_keep'] += 1
        stats['files_to_delete'] += len(newer_files)
        stats['space_total'] += file_size
        stats['space_wasted'] += file_size * len(newer_files)

        for newer_file in newer_files:
            deletion_plan.append((newer_file, oldest_file, file_size))

    return deletion_plan, stats


def print_statistics(stats: Dict, deletion_plan: List):
    """Print detailed statistics."""
    print(f"\n{'='*80}")
    print("DUPLICATE ANALYSIS RESULTS")
    print(f"{'='*80}\n")

    print(f"Duplicate groups found:      {stats['groups']:,}")
    print(f"Total duplicate files:       {stats['total_files']:,}")
    print(f"  - Files to KEEP (oldest):  {stats['files_to_keep']:,}")
    print(f"  - Files to DELETE (newer): {stats['files_to_delete']:,}")
    print()
    print(f"Original data size:          {format_size(stats['space_total'])}")
    print(f"Wasted space (duplicates):   {format_size(stats['space_wasted'])}")
    print(f"Waste percentage:            {(stats['space_wasted']/(stats['space_total']+stats['space_wasted'])*100):.1f}%")
    print()
    print(f"{'='*80}\n")

    # Show first 5 examples
    print("EXAMPLES (first 5 groups):\n")

    groups = defaultdict(list)
    for to_delete, to_keep, size in deletion_plan:
        groups[to_keep].append(to_delete)

    for idx, (keep_file, delete_list) in enumerate(list(groups.items())[:5], 1):
        print(f"Group {idx}:")
        print(f"  KEEP (oldest):   {keep_file}")
        print(f"                   {format_date(get_file_age(keep_file))}")
        for delete_file in delete_list:
            print(f"  DELETE (newer):  {delete_file}")
            print(f"                   {format_date(get_file_age(delete_file))}")
        print()

    if len(groups) > 5:
        print(f"... and {len(groups) - 5} more groups\n")


def save_log(deletion_plan: List, stats: Dict, output_file: str):
    """Save detailed log."""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("DUPLICATE CLEANER - DETAILED LOG\n")
        f.write("="*80 + "\n\n")

        f.write(f"Total duplicate groups: {stats['groups']:,}\n")
        f.write(f"Files to delete: {stats['files_to_delete']:,}\n")
        f.write(f"Space to free: {format_size(stats['space_wasted'])}\n\n")
        f.write("-"*80 + "\n\n")

        groups = defaultdict(list)
        for to_delete, to_keep, size in deletion_plan:
            groups[to_keep].append((to_delete, size))

        for idx, (keep_file, delete_list) in enumerate(sorted(groups.items()), 1):
            f.write(f"Group {idx}\n")
            f.write(f"KEEP (oldest):   {keep_file}\n")
            f.write(f"                 Modified: {format_date(get_file_age(keep_file))}\n")
            f.write(f"                 Size: {format_size(keep_file.stat().st_size)}\n\n")

            for delete_file, size in delete_list:
                f.write(f"DELETE (newer):  {delete_file}\n")
                f.write(f"                 Modified: {format_date(get_file_age(delete_file))}\n")
                f.write(f"                 Size: {format_size(size)}\n\n")

            f.write("-"*80 + "\n\n")


def delete_files(deletion_plan: List) -> Tuple[int, int, int]:
    """
    Delete files (to Recycle Bin if available).
    Returns: (deleted, failed, freed_bytes)
    """
    total = len(deletion_plan)

    print(f"\n{'='*80}")
    print(f"DELETING {total:,} FILES")
    print(f"Method: {'Recycle Bin (SAFE)' if TRASH_AVAILABLE else 'PERMANENT (UNSAFE!)'}")
    print(f"{'='*80}\n")

    deleted = 0
    failed = 0
    freed = 0

    iterator = tqdm(deletion_plan, desc="Deleting", unit=" files") if TQDM_AVAILABLE else deletion_plan

    for to_delete, to_keep, size in iterator:
        try:
            if TRASH_AVAILABLE:
                send2trash(str(to_delete))
            else:
                os.remove(to_delete)

            deleted += 1
            freed += size

        except Exception as e:
            failed += 1
            if not TQDM_AVAILABLE:
                print(f"ERROR: {to_delete}: {e}")

    return deleted, failed, freed


def main():
    """Main entry point."""
    print(f"\n{'='*80}")
    print("ULTIMATE DUPLICATE CLEANER")
    print(f"{'='*80}\n")

    # Select directory
    if sys.platform == 'win32':
        import string
        drives = [f"{l}:\\" for l in string.ascii_uppercase if os.path.exists(f"{l}:\\")]

        if drives:
            print("Available drives:")
            for i, d in enumerate(drives, 1):
                print(f"  {i}. {d}")
            print(f"  {len(drives)+1}. Custom path")
            print()

            while True:
                choice = input(f"Select drive (1-{len(drives)+1}): ").strip()
                try:
                    n = int(choice)
                    if 1 <= n <= len(drives):
                        directory = drives[n-1]
                        break
                    elif n == len(drives)+1:
                        directory = input("Enter path: ").strip().strip('"').strip("'")
                        break
                except:
                    pass
        else:
            directory = input("Enter directory: ").strip().strip('"').strip("'")
    else:
        directory = input("Enter directory: ").strip()

    if not os.path.isdir(directory):
        print(f"\n[ERROR] Directory not found: {directory}")
        return 1

    # Configuration
    skip_patterns = {'$RECYCLE.BIN', 'System Volume Information', 'themes', '$Recycle.Bin'}
    workers = cpu_count()
    log_file = "duplicate_log.txt"

    # STEP 1: Find duplicates
    duplicates = find_duplicates(directory, skip_patterns, workers)

    if not duplicates:
        print("\n[OK] No duplicates found - disk is clean!\n")
        return 0

    # STEP 2: Analyze
    deletion_plan, stats = analyze_duplicates(duplicates)

    # STEP 3: Show statistics
    print_statistics(stats, deletion_plan)

    # STEP 4: Save log
    print(f"Saving detailed log to: {log_file}")
    save_log(deletion_plan, stats, log_file)
    print(f"[OK] Log saved: {log_file}\n")

    # STEP 5: Ask for confirmation
    print(f"{'='*80}")
    print("READY TO DELETE")
    print(f"{'='*80}")
    print(f"Files to delete: {stats['files_to_delete']:,}")
    print(f"Space to free: {format_size(stats['space_wasted'])}")
    print(f"Method: {'Recycle Bin (you can restore)' if TRASH_AVAILABLE else 'PERMANENT deletion (cannot restore!)'}")
    print()
    print("Logic: Keep OLDEST file (original), delete NEWER files (copies)")
    print(f"{'='*80}\n")

    response = input("Delete duplicates? (yes/no): ").strip().lower()

    if response not in ['yes', 'y']:
        print("\n[CANCELLED] No files deleted\n")
        return 0

    # STEP 6: Delete
    deleted, failed, freed = delete_files(deletion_plan)

    # STEP 7: Summary
    print(f"\n{'='*80}")
    print("OPERATION COMPLETE")
    print(f"{'='*80}")
    print(f"Deleted: {deleted:,} files")
    print(f"Freed: {format_size(freed)}")
    if TRASH_AVAILABLE:
        print(f"Location: Recycle Bin (can be restored)")
    if failed > 0:
        print(f"Failed: {failed:,} files")
    print(f"Log: {log_file}")
    print(f"{'='*80}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
