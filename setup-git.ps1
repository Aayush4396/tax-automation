# PowerShell script to set up Git repository and push to GitHub
# Run this script from the project root directory (E:\Tax)

param (
    [string]$RepositoryName = "tax-automation",
    [string]$GitHubUsername,
    [string]$GitHubToken
)

# Check if Git is installed
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Git is not installed. Please install Git first." -ForegroundColor Red
    exit 1
}

# Check if we're in the right directory
$currentDir = Get-Location
if ($currentDir.Path -ne "E:\Tax" -and $currentDir.Path -ne "e:\Tax") {
    Write-Host "Please run this script from E:\Tax (Current: $($currentDir.Path))" -ForegroundColor Red
    exit 1
}

# Initialize Git repository
Write-Host "Initializing Git repository..." -ForegroundColor Cyan
git init

# Add all files
Write-Host "Adding files to Git..." -ForegroundColor Cyan
git add .

# Create initial commit
Write-Host "Creating initial commit..." -ForegroundColor Cyan
git commit -m "Initial commit: Modular tax automation system"

# Check if GitHub credentials are provided
if (-not $GitHubUsername -or -not $GitHubToken) {
    Write-Host "GitHub credentials not provided. Please provide your GitHub username and a personal access token." -ForegroundColor Yellow
    Write-Host "You can create a token at: https://github.com/settings/tokens" -ForegroundColor Yellow
    Write-Host "Required scopes: repo" -ForegroundColor Yellow
    exit 0
}

# Set default branch to main
git branch -M main

# Create remote repository URL
$remoteUrl = "https://${GitHubUsername}:${GitHubToken}@github.com/${GitHubUsername}/${RepositoryName}.git"

# Create repository on GitHub (using API)
Write-Host "Creating GitHub repository..." -ForegroundColor Cyan
try {
    $headers = @{
        "Authorization" = "token $GitHubToken"
        "Accept" = "application/vnd.github.v3+json"
    }
    $body = @{
        name = $RepositoryName
        description = "Modular tax automation system"
        public = $true
        auto_init = $false
    } | ConvertTo-Json

    $response = Invoke-RestMethod -Uri "https://api.github.com/user/repos" -Method Post -Headers $headers -Body $body
    Write-Host "Repository created: $($response.html_url)" -ForegroundColor Green
} catch {
    Write-Host "Failed to create repository: $_" -ForegroundColor Red
    Write-Host "The repository might already exist. Continuing with push..." -ForegroundColor Yellow
}

# Add remote
Write-Host "Adding remote origin..." -ForegroundColor Cyan
if (git remote) {
    git remote remove origin 2>$null
}
git remote add origin $remoteUrl

# Push to GitHub
Write-Host "Pushing to GitHub..." -ForegroundColor Cyan
git push -u origin main

Write-Host "Setup complete!" -ForegroundColor Green
Write-Host "Your repository is available at: https://github.com/$GitHubUsername/$RepositoryName" -ForegroundColor Green
