"""
Dependency management module for FlexibleInputProcessor.
Handles automatic installation and validation of required packages.
"""

import subprocess
import sys
import importlib
import logging
from typing import Dict, List


class DependencyManager:
    """Manages package dependencies and automatic installation."""
    
    def __init__(self, auto_install: bool = True, logger: logging.Logger = None):
        """
        Initialize dependency manager.
        
        Args:
            auto_install (bool): Whether to automatically install missing packages
            logger (logging.Logger): Logger instance for output
        """
        self.auto_install = auto_install
        self.logger = logger or logging.getLogger(__name__)
        
        # Package requirements for different file formats
        self.format_dependencies = {
            'xlsx': ['openpyxl'],
            'xls': ['xlrd'],
            'parquet': ['pyarrow', 'fastparquet'],  # Either one works
            'feather': ['pyarrow'],
            'orc': ['pyarrow'],
            'hdf5': ['tables'],
            'h5': ['tables'],
            'spss': ['pyreadstat'],
            'sas': ['pyreadstat'],  # Optional, pandas has built-in support
        }
    
    def install_package(self, package_name: str) -> bool:
        """
        Install a package using pip.
        
        Args:
            package_name (str): Name of the package to install
            
        Returns:
            bool: True if installation successful, False otherwise
        """
        if not self.auto_install:
            self.logger.info(f"Auto-install disabled. Please install {package_name} manually.")
            return False
            
        try:
            self.logger.info(f"Installing missing dependency: {package_name}")
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", package_name
            ], capture_output=True, text=True)
            self.logger.info(f"Successfully installed {package_name}")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to install {package_name}: {e}")
            return False
    
    def is_package_available(self, package_name: str) -> bool:
        """
        Check if a package is available for import.
        
        Args:
            package_name (str): Name of the package to check
            
        Returns:
            bool: True if package is available, False otherwise
        """
        try:
            importlib.import_module(package_name)
            return True
        except ImportError:
            return False
    
    def ensure_dependency(self, package_name: str) -> bool:
        """
        Ensure a dependency is available, installing if necessary and enabled.
        
        Args:
            package_name (str): Name of the package to check/install
            
        Returns:
            bool: True if package is available, False otherwise
        """
        if self.is_package_available(package_name):
            return True
        
        if self.auto_install:
            return self.install_package(package_name)
        else:
            self.logger.error(
                f"Missing dependency: {package_name}. "
                f"Install with: pip install {package_name}"
            )
            return False
    
    def ensure_format_dependencies(self, file_format: str) -> bool:
        """
        Ensure all dependencies for a file format are available.
        
        Args:
            file_format (str): File format (e.g., 'xlsx', 'parquet')
            
        Returns:
            bool: True if at least one required dependency is available
        """
        if file_format not in self.format_dependencies:
            return True  # No special dependencies required
        
        required_packages = self.format_dependencies[file_format]
        
        # For formats with multiple options (like parquet), try each one
        for package in required_packages:
            if self.ensure_dependency(package):
                return True
        
        # If we get here, none of the required packages are available
        self.logger.error(
            f"No suitable dependencies available for {file_format} format. "
            f"Required: {required_packages}"
        )
        return False
    
    def get_available_formats(self) -> Dict[str, bool]:
        """
        Get a dictionary of file formats and their availability.
        
        Returns:
            Dict[str, bool]: Dictionary mapping format to availability
        """
        availability = {}
        
        for file_format, packages in self.format_dependencies.items():
            availability[file_format] = any(
                self.is_package_available(pkg) for pkg in packages
            )
        
        # Add formats that don't need special dependencies
        basic_formats = ['csv', 'tsv', 'txt', 'json', 'pkl', 'pickle', 'dta']
        for fmt in basic_formats:
            availability[fmt] = True
        
        return availability
    
    def install_all_optional_dependencies(self) -> Dict[str, bool]:
        """
        Attempt to install all optional dependencies.
        
        Returns:
            Dict[str, bool]: Installation results for each package
        """
        if not self.auto_install:
            self.logger.info("Auto-install disabled. Skipping dependency installation.")
            return {}
        
        all_packages = set()
        for packages in self.format_dependencies.values():
            all_packages.update(packages)
        
        results = {}
        for package in all_packages:
            if not self.is_package_available(package):
                results[package] = self.install_package(package)
            else:
                results[package] = True  # Already available
        
        return results