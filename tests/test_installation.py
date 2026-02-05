"""
Test installation and basic functionality
"""

import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")

    try:
        # Test data collectors
        from src.data_collector import (
            CompanyInfoCollector,
            FinancialDataCollector,
            MarketDataCollector,
            NewsCollector,
        )

        print("  ✓ Data collectors imported")

        # Test features
        from src.features import FinancialFeatureExtractor

        print("  ✓ Feature extractors imported")

        # Test LLM
        from src.llm import LLMInterface, PromptTemplates

        print("  ✓ LLM modules imported")

        # Test pipeline
        from src.pipeline import CreditRiskPredictor

        print("  ✓ Pipeline imported")

        return True

    except ImportError as e:
        print(f"  ✗ Import error: {e}")
        return False


def test_config():
    """Test that config file exists and is valid"""
    print("\nTesting configuration...")

    try:
        import yaml

        config_path = Path("config/config.yaml")
        if not config_path.exists():
            print(f"  ✗ Config file not found: {config_path}")
            return False

        with open(config_path) as f:
            config = yaml.safe_load(f)

        # Check required sections
        required_sections = ["llm", "data_sources", "prediction", "companies"]
        for section in required_sections:
            if section not in config:
                print(f"  ✗ Missing config section: {section}")
                return False

        print("  ✓ Configuration valid")
        return True

    except Exception as e:
        print(f"  ✗ Config error: {e}")
        return False


def test_env():
    """Test environment setup"""
    print("\nTesting environment...")

    try:
        from dotenv import load_dotenv
        import os

        env_path = Path(".env")
        if not env_path.exists():
            print("  ⚠ .env file not found (required for API keys)")
            print("    Copy .env.example to .env and add your API keys")
            return False

        load_dotenv()

        # Check for API keys
        has_openai = bool(os.getenv("OPENAI_API_KEY"))
        has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))

        if has_openai:
            print("  ✓ OpenAI API key found")
        if has_anthropic:
            print("  ✓ Anthropic API key found")

        if not (has_openai or has_anthropic):
            print("  ⚠ No API keys found in .env")
            print("    Add at least one API key to use the pipeline")
            return False

        return True

    except Exception as e:
        print(f"  ✗ Environment error: {e}")
        return False


def test_dependencies():
    """Test that all dependencies are installed"""
    print("\nTesting dependencies...")

    required_packages = [
        "openai",
        "anthropic",
        "pandas",
        "numpy",
        "requests",
        "yfinance",
        "loguru",
        "yaml",
    ]

    all_installed = True
    for package in required_packages:
        try:
            if package == "yaml":
                __import__("yaml")
            else:
                __import__(package)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package} not installed")
            all_installed = False

    return all_installed


def test_directories():
    """Test that required directories exist"""
    print("\nTesting directory structure...")

    required_dirs = [
        "src",
        "src/data_collector",
        "src/features",
        "src/llm",
        "src/pipeline",
        "config",
        "data",
        "data/raw",
        "data/processed",
        "data/results",
    ]

    all_exist = True
    for dir_path in required_dirs:
        path = Path(dir_path)
        if path.exists():
            print(f"  ✓ {dir_path}")
        else:
            print(f"  ✗ {dir_path} not found")
            all_exist = False

    return all_exist


def main():
    """Run all tests"""
    print("=" * 60)
    print("Credit Risk Pipeline - Installation Test")
    print("=" * 60)

    tests = [
        ("Dependencies", test_dependencies),
        ("Directory Structure", test_directories),
        ("Module Imports", test_imports),
        ("Configuration", test_config),
        ("Environment", test_env),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} failed with error: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("\n✓ All tests passed! Installation is complete.")
        print("\nNext steps:")
        print("1. Ensure .env file has your API keys")
        print("2. Run 'python main.py' to start the pipeline")
        print("3. Or run 'python example.py' for example usage")
    else:
        print("\n⚠ Some tests failed. Please fix the issues above.")

    print("=" * 60 + "\n")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
