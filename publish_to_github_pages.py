#!/usr/bin/env python3
"""
GitHub Pages Publisher for RingCX gRPC Streaming Guide

This script converts the Markdown guide to HTML and sets up GitHub Pages deployment.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import markdown
import re

def run_command(command, check=True, capture_output=True):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=check, 
            capture_output=capture_output,
            text=True
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        print(f"Error: {e}")
        if capture_output:
            print(f"stdout: {e.stdout}")
            print(f"stderr: {e.stderr}")
        return None

def install_dependencies():
    """Install required Python packages."""
    print("Installing dependencies...")
    packages = ["markdown", "PyGithub"]
    
    for package in packages:
        try:
            import importlib
            importlib.import_module(package.replace("-", "_"))
            print(f"✓ {package} already installed")
        except ImportError:
            print(f"Installing {package}...")
            result = run_command(f"pip install {package}")
            if result is None:
                print(f"Failed to install {package}")
                return False
    return True

def create_html_template():
    """Create an HTML template for the GitHub Pages site."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RingCX gRPC Streaming Implementation Guide</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.2.0/github-markdown.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css">
    <style>
        :root {{
            --primary-color: #2563eb;
            --primary-hover: #1d4ed8;
            --secondary-color: #64748b;
            --accent-color: #f59e0b;
            --background-color: #ffffff;
            --surface-color: #f8fafc;
            --border-color: #e2e8f0;
            --text-primary: #1e293b;
            --text-secondary: #64748b;
            --code-bg: #1e293b;
            --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
            --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
            --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
        }}

        * {{
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: var(--text-primary);
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 0;
            min-height: 100vh;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }}

        .header {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid var(--border-color);
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: var(--shadow-sm);
        }}

        .header-content {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem 2rem;
        }}

        .logo {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            text-decoration: none;
            color: var(--text-primary);
        }}

        .logo-icon {{
            width: 40px;
            height: 40px;
            background: linear-gradient(135deg, var(--primary-color), var(--accent-color));
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 1.2rem;
        }}

        .logo-text {{
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--text-primary);
        }}

        .main-content {{
            background: var(--background-color);
            border-radius: 16px;
            box-shadow: var(--shadow-lg);
            margin: 2rem auto;
            overflow: hidden;
            max-width: 1000px;
        }}

        .markdown-body {{
            box-sizing: border-box;
            min-width: 200px;
            max-width: none;
            margin: 0;
            padding: 3rem;
            background: var(--background-color);
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.7;
            color: var(--text-primary);
        }}

        .markdown-body h1 {{
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 3px solid var(--primary-color);
            background: linear-gradient(135deg, var(--primary-color), var(--accent-color));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}

        .markdown-body h2 {{
            font-size: 1.8rem;
            font-weight: 600;
            color: var(--text-primary);
            margin-top: 2.5rem;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid var(--border-color);
        }}

        .markdown-body h3 {{
            font-size: 1.4rem;
            font-weight: 600;
            color: var(--text-primary);
            margin-top: 2rem;
            margin-bottom: 0.75rem;
        }}

        .markdown-body h4 {{
            font-size: 1.2rem;
            font-weight: 600;
            color: var(--text-primary);
            margin-top: 1.5rem;
            margin-bottom: 0.5rem;
        }}

        .markdown-body p {{
            margin-bottom: 1.25rem;
            color: var(--text-secondary);
        }}

        .markdown-body strong {{
            color: var(--text-primary);
            font-weight: 600;
        }}

        .markdown-body code {{
            background: var(--surface-color);
            color: var(--primary-color);
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            font-size: 0.875rem;
            font-weight: 500;
            border: 1px solid var(--border-color);
        }}

        .markdown-body pre {{
            background: var(--code-bg);
            border-radius: 8px;
            padding: 1.5rem;
            overflow-x: auto;
            border: 1px solid var(--border-color);
            box-shadow: var(--shadow-md);
        }}

        .markdown-body pre code {{
            background: none;
            color: #e2e8f0;
            padding: 0;
            border: none;
            font-size: 0.875rem;
        }}

        .markdown-body blockquote {{
            background: linear-gradient(135deg, var(--primary-color), var(--accent-color));
            color: white;
            padding: 1.5rem;
            border-radius: 8px;
            margin: 1.5rem 0;
            border-left: 4px solid var(--accent-color);
            box-shadow: var(--shadow-md);
        }}

        .markdown-body blockquote p {{
            color: white;
            margin: 0;
        }}

        .markdown-body table {{
            border-collapse: collapse;
            width: 100%;
            margin: 1.5rem 0;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: var(--shadow-sm);
        }}

        .markdown-body th {{
            background: var(--primary-color);
            color: white;
            padding: 1rem;
            text-align: left;
            font-weight: 600;
        }}

        .markdown-body td {{
            padding: 1rem;
            border-bottom: 1px solid var(--border-color);
            background: var(--background-color);
        }}

        .markdown-body tr:nth-child(even) td {{
            background: var(--surface-color);
        }}

        .markdown-body ul, .markdown-body ol {{
            padding-left: 1.5rem;
            margin-bottom: 1.25rem;
        }}

        .markdown-body li {{
            margin-bottom: 0.5rem;
            color: var(--text-secondary);
        }}

        .markdown-body a {{
            color: var(--primary-color);
            text-decoration: none;
            font-weight: 500;
            transition: color 0.2s ease;
        }}

        .markdown-body a:hover {{
            color: var(--primary-hover);
            text-decoration: underline;
        }}

        .github-corner {{
            position: fixed;
            top: 0;
            right: 0;
            z-index: 1000;
        }}

        .github-corner:hover .octo-arm {{
            animation: octocat-wave 560ms ease-in-out;
        }}

        @keyframes octocat-wave {{
            0%, 100% {{ transform: rotate(0); }}
            20%, 60% {{ transform: rotate(-25deg); }}
            40%, 80% {{ transform: rotate(10deg); }}
        }}

        .github-corner svg {{
            fill: var(--primary-color);
            color: white;
            position: fixed;
            top: 0;
            border: 0;
            right: 0;
        }}

        .github-corner .octo-arm {{
            transform-origin: 130px 106px;
        }}

        .footer {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-top: 1px solid var(--border-color);
            padding: 2rem;
            text-align: center;
            color: var(--text-secondary);
            margin-top: 3rem;
        }}

        .footer-content {{
            max-width: 1000px;
            margin: 0 auto;
        }}

        .footer a {{
            color: var(--primary-color);
            text-decoration: none;
            font-weight: 500;
        }}

        .footer a:hover {{
            text-decoration: underline;
        }}

        @media (max-width: 768px) {{
            .container {{
                padding: 1rem;
            }}
            
            .header-content {{
                padding: 1rem;
            }}
            
            .markdown-body {{
                padding: 1.5rem;
            }}
            
            .markdown-body h1 {{
                font-size: 2rem;
            }}
            
            .markdown-body h2 {{
                font-size: 1.5rem;
            }}
            
            .logo-text {{
                font-size: 1.2rem;
            }}
        }}

        /* Custom scrollbar */
        ::-webkit-scrollbar {{
            width: 8px;
        }}

        ::-webkit-scrollbar-track {{
            background: var(--surface-color);
        }}

        ::-webkit-scrollbar-thumb {{
            background: var(--primary-color);
            border-radius: 4px;
        }}

        ::-webkit-scrollbar-thumb:hover {{
            background: var(--primary-hover);
        }}

        /* Syntax highlighting improvements */
        .highlight {{
            background: var(--code-bg);
            border-radius: 8px;
            padding: 1.5rem;
            margin: 1.5rem 0;
            overflow-x: auto;
            border: 1px solid var(--border-color);
            box-shadow: var(--shadow-md);
        }}

        .highlight pre {{
            background: none;
            padding: 0;
            margin: 0;
        }}

        /* Alert boxes */
        .alert {{
            padding: 1rem 1.5rem;
            border-radius: 8px;
            margin: 1.5rem 0;
            border-left: 4px solid;
        }}

        .alert-info {{
            background: rgba(59, 130, 246, 0.1);
            border-left-color: var(--primary-color);
            color: var(--primary-color);
        }}

        .alert-warning {{
            background: rgba(245, 158, 11, 0.1);
            border-left-color: var(--accent-color);
            color: #92400e;
        }}

        .alert-success {{
            background: rgba(34, 197, 94, 0.1);
            border-left-color: #22c55e;
            color: #166534;
        }}
    </style>
</head>
<body>
    <a href="https://github.com/DaKingKong/RingCX-gRPC-bot-guide" class="github-corner" aria-label="View source on GitHub">
        <svg width="80" height="80" viewBox="0 0 250 250" aria-hidden="true">
            <path d="M0,0 L115,115 L130,115 L142,142 L250,250 L250,0 Z"></path>
            <path d="M128.3,109.0 C113.8,99.7 119.0,89.6 119.0,89.6 C122.0,82.7 120.5,78.6 120.5,78.6 C119.2,72.0 123.4,76.3 123.4,76.3 C127.3,80.9 125.5,87.3 125.5,87.3 C122.9,97.6 130.6,101.9 134.4,103.2" fill="currentColor" style="transform-origin: 130px 106px;" class="octo-arm"></path>
            <path d="M115.0,115.0 C114.9,115.1 118.7,116.5 119.8,115.4 L133.7,101.6 C136.9,99.2 139.9,98.4 142.2,98.6 C133.8,88.0 127.5,74.4 143.8,58.0 C148.5,53.4 154.0,51.2 159.7,51.0 C160.3,49.4 163.2,43.6 171.4,40.1 C171.4,40.1 176.1,42.5 178.8,56.2 C183.1,58.6 187.2,61.8 190.9,65.4 C194.5,69.0 197.7,73.2 200.1,77.6 C213.8,80.2 216.3,84.9 216.3,84.9 C212.7,91.3 206.9,94.7 205.4,96.6 C205.1,102.4 203.0,107.8 198.3,112.5 C181.9,128.9 168.3,122.5 157.7,114.1 C157.9,116.9 156.7,120.9 152.7,124.9 L141.0,136.5 C139.8,137.7 141.6,141.9 141.8,141.8 Z" fill="currentColor" class="octo-body"></path>
        </svg>
    </a>

    <header class="header">
        <div class="header-content">
            <a href="#" class="logo">
                <div class="logo-icon">R</div>
                <div class="logo-text">RingCX Guide</div>
            </a>
        </div>
    </header>

    <div class="container">
        <main class="main-content">
            <article class="markdown-body">
                {content}
            </article>
        </main>
    </div>

    <footer class="footer">
        <div class="footer-content">
            <p>Built with ❤️ for the RingCX community</p>
            <p>View the source on <a href="https://github.com/DaKingKong/RingCX-gRPC-bot-guide">GitHub</a></p>
        </div>
    </footer>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-core.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/plugins/autoloader/prism-autoloader.min.js"></script>
</body>
</html>"""

def convert_markdown_to_html(markdown_file):
    """Convert Markdown file to HTML."""
    print(f"Converting {markdown_file} to HTML...")
    
    # Read the markdown file
    with open(markdown_file, 'r', encoding='utf-8') as f:
        markdown_content = f.read()
    
    # Configure markdown extensions
    extensions = [
        'markdown.extensions.codehilite',
        'markdown.extensions.fenced_code',
        'markdown.extensions.tables',
        'markdown.extensions.toc',
        'markdown.extensions.def_list',
        'markdown.extensions.abbr',
        'markdown.extensions.footnotes'
    ]
    
    # Convert markdown to HTML
    html_content = markdown.markdown(
        markdown_content,
        extensions=extensions,
        extension_configs={
            'codehilite': {
                'css_class': 'highlight',
                'use_pygments': True,
                'noclasses': True
            }
        }
    )
    
    # Get the HTML template
    template = create_html_template()
    
    # Insert the content into the template
    final_html = template.format(content=html_content)
    
    return final_html

def setup_github_pages():
    """Set up GitHub Pages configuration."""
    print("Setting up GitHub Pages...")
    
    # Create docs directory if it doesn't exist
    docs_dir = Path("docs")
    docs_dir.mkdir(exist_ok=True)
    
    # Create index.html in docs directory
    markdown_file = "RingCX_gRPC_Streaming_Guide.md"
    html_content = convert_markdown_to_html(markdown_file)
    
    with open(docs_dir / "index.html", 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print("✓ Created docs/index.html")
    
    # Create a simple README for the docs directory
    docs_readme = """# RingCX gRPC Streaming Guide

This directory contains the GitHub Pages site for the RingCX gRPC Streaming Implementation Guide.

The main content is in `index.html` which is automatically generated from the Markdown file.
"""
    
    with open(docs_dir / "README.md", 'w', encoding='utf-8') as f:
        f.write(docs_readme)
    
    print("✓ Created docs/README.md")

def create_github_workflow():
    """Create GitHub Actions workflow for automatic deployment."""
    print("Creating GitHub Actions workflow...")
    
    # Create .github/workflows directory
    workflows_dir = Path(".github/workflows")
    workflows_dir.mkdir(parents=True, exist_ok=True)
    
    workflow_content = """name: Deploy to GitHub Pages

on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - name: Checkout
      uses: actions/checkout@v4
      
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
        
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install markdown PyGithub
        
    - name: Generate HTML
      run: |
        python publish_to_github_pages.py --generate-only
        
    - name: Setup Pages
      uses: actions/configure-pages@v4
      
    - name: Upload artifact
      uses: actions/upload-pages-artifact@v3
      with:
        path: './docs'

  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/main' || github.ref == 'refs/heads/master'
    steps:
    - name: Deploy to GitHub Pages
      id: deployment
      uses: actions/deploy-pages@v4
"""
    
    with open(workflows_dir / "deploy.yml", 'w', encoding='utf-8') as f:
        f.write(workflow_content)
    
    print("✓ Created .github/workflows/deploy.yml")

def update_repository_settings():
    """Provide instructions for updating repository settings."""
    print("\n" + "="*60)
    print("GITHUB PAGES SETUP INSTRUCTIONS")
    print("="*60)
    print("""
To enable GitHub Pages for your repository:

1. Go to your repository on GitHub
2. Click on "Settings" tab
3. Scroll down to "Pages" section in the left sidebar
4. Under "Source", select "Deploy from a branch"
5. Choose "main" or "master" branch
6. Select "/docs" folder
7. Click "Save"

Alternatively, you can use GitHub Actions (recommended):
- The workflow file has been created at .github/workflows/deploy.yml
- It will automatically deploy when you push to main/master branch
- Make sure to enable GitHub Actions in your repository settings

Your site will be available at: https://DaKingKong.github.io/RingCX-gRPC-bot-guide/
""")

def main():
    """Main function."""
    print("RingCX gRPC Streaming Guide - GitHub Pages Publisher")
    print("=" * 55)
    
    # Check if we're in a git repository
    if not Path(".git").exists():
        print("Error: This script must be run from a Git repository.")
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        print("Error: Failed to install dependencies.")
        sys.exit(1)
    
    # Check command line arguments
    generate_only = "--generate-only" in sys.argv
    
    if generate_only:
        print("Generating HTML only...")
        setup_github_pages()
        print("✓ HTML generation complete!")
    else:
        # Full setup
        setup_github_pages()
        create_github_workflow()
        update_repository_settings()
        
        print("\n" + "="*60)
        print("NEXT STEPS")
        print("="*60)
        print("""
1. Commit and push your changes:
   git add .
   git commit -m "Add GitHub Pages setup"
   git push origin main

2. Follow the GitHub Pages setup instructions above

3. Your guide will be available at your GitHub Pages URL
""")

if __name__ == "__main__":
    main() 