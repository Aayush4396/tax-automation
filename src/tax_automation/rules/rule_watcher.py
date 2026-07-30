# -*- coding: utf-8 -*-
"""
rule_watcher.py
================

Rule hot-reloading implementation using file system monitoring.

This module provides functionality to watch rule configuration files
and automatically reload them when changes are detected.
"""

from __future__ import annotations
import os
import time
import threading
from pathlib import Path
from typing import Callable, Dict, List, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class RuleChangeHandler(FileSystemEventHandler):
    """Handles file system events for rule configuration files."""

    def __init__(self, callback: Callable[[str], None]):
        self.callback = callback

    def on_modified(self, event):
        """Called when a file is modified."""
        if not event.is_directory and event.src_path.endswith((".yaml", ".yml", ".json")):
            self.callback(event.src_path)


class RuleWatcher:
    """Watches rule configuration files for changes and triggers reloads."""

    def __init__(self, watch_dirs: List[str], reload_callback: Callable[[str], None]):
        """
        Initialize the rule watcher.

        Args:
            watch_dirs: List of directories to watch for rule changes
            reload_callback: Function to call when a rule file changes
        """
        self.watch_dirs = [Path(d) for d in watch_dirs]
        self.reload_callback = reload_callback
        self.observer: Optional[Observer] = None
        self.watch_thread: Optional[threading.Thread] = None
        self.running = False

    def start(self) -> None:
        """Start watching for rule file changes."""
        if self.running:
            return

        self.running = True
        self.observer = Observer()
        event_handler = RuleChangeHandler(self.reload_callback)

        for watch_dir in self.watch_dirs:
            if watch_dir.exists():
                self.observer.schedule(event_handler, str(watch_dir), recursive=True)

        self.watch_thread = threading.Thread(target=self.observer.start, daemon=True)
        self.watch_thread.start()

    def stop(self) -> None:
        """Stop watching for rule file changes."""
        if not self.running:
            return

        self.running = False
        if self.observer:
            self.observer.stop()
        if self.watch_thread:
            self.watch_thread.join(timeout=5)

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


def create_rule_watcher(
    config_dirs: List[str],
    reload_callback: Callable[[str], None]
) -> RuleWatcher:
    """
    Factory function to create a rule watcher instance.

    Args:
        config_dirs: List of directories containing rule configuration files
        reload_callback: Function to call when rules change

    Returns:
        Configured RuleWatcher instance
    """
    return RuleWatcher(config_dirs, reload_callback)


def watch_rules_in_background(
    watch_dirs: List[str],
    reload_callback: Callable[[str], None]
) -> RuleWatcher:
    """
    Start watching rules in the background.

    Args:
        watch_dirs: Directories to watch
        reload_callback: Function to call on rule changes

    Returns:
        RuleWatcher instance
    """
    watcher = create_rule_watcher(watch_dirs, reload_callback)
    watcher.start()
    return watcher