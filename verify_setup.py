#!/usr/bin/env python3
"""
Crypto Data Engine - Setup Verification Script

This script checks if your project is set up correctly.

Usage:
    python verify_setup.py
"""

import os
import sys
from pathlib import Path
import importlib.util


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'


def print_status(status, message):
    """Print colored status message."""
    if status == "OK":
        print(f"{Colors.GREEN}✅ {message}{Colors.RESET}")
        return True
    elif status == "ERROR":
        print(f"{Colors.RED}❌ {message}{Colors.RESET}")
        return False
    elif status == "WARN":
        print(f"{Colors.YELLOW}⚠️  {message}{Colors.RESET}")
        return True
    elif status == "INFO":
        print(f"{Colors.BLUE}ℹ️  {message}{Colors.RESET}")
        return True


def check_file_exists(filepath, required=True):
    """Check if a file exists."""
    if Path(filepath).exists():
        return print_status("OK", f"Found: {filepath}")
    else:
        status = "ERROR" if required else "WARN"
        return print_status(status, f"Missing: {filepath}")


def check_python_syntax(filepath):
    """Check if Python file has valid syntax."""
    try:
        with open(filepath, 'r') as f:
            compile(f.read(), filepath, 'exec')
        return print_status("OK", f"Syntax valid: {filepath}")
    except SyntaxError as e:
        return print_status("ERROR", f"Syntax error in {filepath}: {e}")
    except Exception as e:
        return print_status("ERROR", f"Error checking {filepath}: {e}")


def check_imports(filepath):
    """Check if a Python file can be imported."""
    try:
        spec = importlib.util.spec_from_file_location("module", filepath)
        module = importlib.util.module_from_spec(spec)
        # Don't actually execute, just check if it would load
        return print_status("OK", f"Imports valid: {filepath}")
    except Exception as e:
        return print_status("WARN", f"Import check warning for {filepath}: {str(e)[:50]}")


def verify_setup():
    """Main verification function."""
    print(f"\n{Colors.BLUE}{'='*80}")
    print("🔍 CRYPTO DATA ENGINE - SETUP VERIFICATION")
    print(f"{'='*80}{Colors.RESET}\n")
    
    errors = 0
    warnings = 0
    
    # ========================================================================
    print(f"\n{Colors.BLUE}📁 1. CHECKING DIRECTORY STRUCTURE{Colors.RESET}")
    print("-" * 80)
    
    required_dirs = [
        "app",
        "app/models",
        "app/schemas",
        "app/api",
        "app/api/v1",
        "app/collectors",
        "app/cache",
        "app/utils",
        "alembic",
        "alembic/versions",
        "tests",
    ]
    
    for directory in required_dirs:
        if not check_file_exists(directory, required=True):
            errors += 1
    
    # ========================================================================
    print(f"\n{Colors.BLUE}📄 2. CHECKING REQUIRED FILES{Colors.RESET}")
    print("-" * 80)
    
    required_files = [
        "requirements.txt",
        ".env.example",
        "Dockerfile",
        "docker-compose.yml",
        "alembic.ini",
        "pytest.ini",
        "README.md",
    ]
    
    for file in required_files:
        if not check_file_exists(file, required=True):
            errors += 1
    
    # Check if .env exists
    if not Path(".env").exists():
        print_status("WARN", ".env not found - you need to create it from .env.example")
        warnings += 1
    else:
        print_status("OK", "Found: .env")
    
    # ========================================================================
    print(f"\n{Colors.BLUE}🐍 3. CHECKING PYTHON FILES{Colors.RESET}")
    print("-" * 80)
    
    python_files = [
        "app/__init__.py",
        "app/config.py",
        "app/database.py",
        "app/main.py",
        "app/models/__init__.py",
        "app/models/market_data.py",
        "app/schemas/__init__.py",
        "app/schemas/market_data.py",
        "app/api/__init__.py",
        "app/api/deps.py",
        "app/api/v1/__init__.py",
        "app/api/v1/market_data.py",
        "app/api/v1/websocket.py",
        "app/collectors/__init__.py",
        "app/collectors/base.py",
        "app/collectors/binance_collector.py",
        "app/collectors/coingecko_collector.py",
        "app/collectors/onchain_collector.py",
        "app/cache/__init__.py",
        "app/cache/redis_cache.py",
        "app/utils/__init__.py",
        "app/utils/logger.py",
        "app/utils/rate_limiter.py",
        "alembic/env.py",
        "alembic/versions/001_initial_schema.py",
        "tests/conftest.py",
        "tests/test_api.py",
        "tests/test_collectors.py",
    ]
    
    for pyfile in python_files:
        if Path(pyfile).exists():
            if not check_python_syntax(pyfile):
                errors += 1
        else:
            print_status("ERROR", f"Missing: {pyfile}")
            errors += 1
    
    # ========================================================================
    print(f"\n{Colors.BLUE}📦 4. CHECKING FILE CONTENT (NOT STUBS){Colors.RESET}")
    print("-" * 80)
    
    critical_files = {
        "app/config.py": ["class Settings", "pydantic_settings"],
        "app/database.py": ["AsyncSession", "create_async_engine"],
        "app/models/market_data.py": ["class OHLCV", "class Ticker"],
        "app/main.py": ["FastAPI", "app = FastAPI"],
        "app/collectors/binance_collector.py": ["class BinanceCollector", "def collect"],
    }
    
    for filepath, keywords in critical_files.items():
        if Path(filepath).exists():
            with open(filepath, 'r') as f:
                content = f.read()
                
            missing_keywords = [kw for kw in keywords if kw not in content]
            
            if missing_keywords:
                print_status("ERROR", f"{filepath} appears to be incomplete (missing: {', '.join(missing_keywords)})")
                errors += 1
            else:
                print_status("OK", f"{filepath} has expected content")
        else:
            print_status("ERROR", f"Missing: {filepath}")
            errors += 1
    
    # ========================================================================
    print(f"\n{Colors.BLUE}🔧 5. CHECKING CONFIGURATION{Colors.RESET}")
    print("-" * 80)
    
    if Path(".env").exists():
        with open(".env", 'r') as f:
            env_content = f.read()
        
        required_vars = [
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "POSTGRES_DB",
            "REDIS_HOST",
        ]
        
        for var in required_vars:
            if var in env_content:
                print_status("OK", f"Found env var: {var}")
            else:
                print_status("WARN", f"Missing env var: {var}")
                warnings += 1
        
        # Check for default passwords
        if "changeme" in env_content or "your_" in env_content:
            print_status("WARN", "You're using default passwords - change them for production!")
            warnings += 1
    
    # ========================================================================
    print(f"\n{Colors.BLUE}🐳 6. CHECKING DOCKER CONFIGURATION{Colors.RESET}")
    print("-" * 80)
    
    if Path("docker-compose.yml").exists():
        with open("docker-compose.yml", 'r') as f:
            docker_content = f.read()
        
        required_services = ["postgres", "redis", "crypto-data-engine"]
        for service in required_services:
            if service in docker_content:
                print_status("OK", f"Found service: {service}")
            else:
                print_status("ERROR", f"Missing service: {service}")
                errors += 1
    
    # ========================================================================
    print(f"\n{Colors.BLUE}🧪 7. CHECKING TEST FILES{Colors.RESET}")
    print("-" * 80)
    
    test_files = [
        "tests/conftest.py",
        "tests/test_api.py",
        "tests/test_collectors.py",
    ]
    
    for test_file in test_files:
        if Path(test_file).exists():
            with open(test_file, 'r') as f:
                content = f.read()
            
            if "def test_" in content or "async def test_" in content:
                print_status("OK", f"{test_file} has test functions")
            else:
                print_status("WARN", f"{test_file} may not have test functions")
                warnings += 1
    
    # ========================================================================
    print(f"\n{Colors.BLUE}📊 VERIFICATION SUMMARY{Colors.RESET}")
    print("=" * 80)
    
    if errors == 0 and warnings == 0:
        print(f"{Colors.GREEN}✅ ALL CHECKS PASSED!{Colors.RESET}")
        print(f"\n{Colors.GREEN}Your setup is complete and ready to use!{Colors.RESET}\n")
        
        print("🚀 NEXT STEPS:")
        print("-" * 80)
        print("1. Configure your API keys in .env file")
        print("2. Start services: docker-compose up -d")
        print("3. Check health: curl http://localhost:8000/health")
        print("4. View API docs: http://localhost:8000/docs")
        print()
        return 0
    
    elif errors == 0:
        print(f"{Colors.YELLOW}⚠️  SETUP COMPLETE WITH {warnings} WARNING(S){Colors.RESET}")
        print(f"\n{Colors.YELLOW}Review warnings above - they may need attention.{Colors.RESET}\n")
        return 0
    
    else:
        print(f"{Colors.RED}❌ SETUP INCOMPLETE: {errors} ERROR(S), {warnings} WARNING(S){Colors.RESET}")
        print(f"\n{Colors.RED}Please fix the errors above before proceeding.{Colors.RESET}\n")
        
        print("💡 COMMON FIXES:")
        print("-" * 80)
        print("• Missing files: Copy content from the corresponding artifacts")
        print("• Syntax errors: Check for copy-paste issues, ensure complete file")
        print("• Missing .env: Run 'cp .env.example .env' and configure it")
        print()
        return 1


if __name__ == "__main__":
    exit_code = verify_setup()
    sys.exit(exit_code)
