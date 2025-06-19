# RingCX gRPC Streaming Implementation Guide

This repository contains a comprehensive guide for implementing gRPC streaming services for RingCX, allowing you to receive real-time audio streams from calls.

## 📖 Documentation

The complete guide is available in [RingCX_gRPC_Streaming_Guide.md](RingCX_gRPC_Streaming_Guide.md).

## 🌐 GitHub Pages

This guide is automatically published to GitHub Pages for easy online viewing.

### View Online
Visit: https://DaKingKong.github.io/RingCX-gRPC-bot-guide/

### Local Development
To view the guide locally or make changes:

1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run the publisher: `python publish_to_github_pages.py`
4. Open `docs/index.html` in your browser

## 🚀 Publishing to GitHub Pages

This repository includes an automated Python script to publish the Markdown guide to GitHub Pages.

### Quick Start

1. **Run the publisher script:**
   ```bash
   python publish_to_github_pages.py
   ```

2. **Commit and push the changes:**
   ```bash
   git add .
   git commit -m "Add GitHub Pages setup"
   git push origin main
   ```

3. **Enable GitHub Pages:**
   - Go to your repository Settings
   - Navigate to Pages section
   - Select "Deploy from a branch"
   - Choose "main" branch and "/docs" folder
   - Save the settings

### What the Script Does

The `publish_to_github_pages.py` script:

- ✅ Converts the Markdown guide to HTML with GitHub-style formatting
- ✅ Creates a `docs/` directory with the generated site
- ✅ Sets up GitHub Actions workflow for automatic deployment
- ✅ Provides step-by-step instructions for GitHub Pages setup

### Features

- **Beautiful Styling**: Uses GitHub's markdown CSS for consistent, professional appearance
- **Code Highlighting**: Syntax highlighting for code blocks
- **Responsive Design**: Works on desktop and mobile devices
- **GitHub Corner**: Links back to the repository
- **Automatic Deployment**: GitHub Actions workflow for continuous deployment

### Manual Steps

If you prefer to set up GitHub Pages manually:

1. **Generate HTML only:**
   ```bash
   python publish_to_github_pages.py --generate-only
   ```

2. **Enable GitHub Pages in repository settings:**
   - Source: Deploy from a branch
   - Branch: main
   - Folder: /docs

## 📁 Repository Structure

```
RingCX-gRPC-bot-guide/
├── RingCX_gRPC_Streaming_Guide.md    # Main guide content
├── publish_to_github_pages.py        # Publisher script
├── requirements.txt                   # Python dependencies
├── docs/                             # Generated GitHub Pages site
│   ├── index.html                    # Main HTML page
│   └── README.md                     # Docs directory info
└── .github/workflows/                # GitHub Actions
    └── deploy.yml                    # Deployment workflow
```

## 🔧 Customization

### Updating the Guide

1. Edit `RingCX_gRPC_Streaming_Guide.md`
2. Run `python publish_to_github_pages.py --generate-only`
3. Commit and push changes

### Custom Styling

Edit the `create_html_template()` function in `publish_to_github_pages.py` to customize the appearance.

### Repository URL

Update the GitHub corner link in the HTML template to match your repository URL.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test the publisher script
5. Submit a pull request

## 📞 Support

For questions about the RingCX gRPC streaming implementation, please contact your RingCX representative.

For issues with the GitHub Pages publisher, please open an issue in this repository. 