# Auto-increment version and commit script (PowerShell)
param(
    [string]$Type = "patch"  # patch, minor, or major
)

Write-Host "🏷️ Auto-version and commit script" -ForegroundColor Cyan

# Function to increment version
function Get-NextVersion {
    param($CurrentTag, $IncrementType)
    
    if ($CurrentTag -match "^v(\d+)\.(\d+)\.(\d+)$") {
        $major = [int]$matches[1]
        $minor = [int]$matches[2] 
        $patch = [int]$matches[3]
        
        switch ($IncrementType) {
            "major" { return "v$($major + 1).0.0" }
            "minor" { return "v$major.$($minor + 1).0" }
            "patch" { return "v$major.$minor.$($patch + 1)" }
            default { return "v$major.$minor.$($patch + 1)" }
        }
    } else {
        return "v0.1.0"
    }
}

try {
    # Get the latest version tag
    $latestTag = git describe --tags --abbrev=0 2>$null
    if (-not $latestTag) { $latestTag = "v0.0.0" }
    
    Write-Host "Current version: $latestTag" -ForegroundColor Yellow
    
    # Calculate new version
    $newTag = Get-NextVersion $latestTag $Type
    Write-Host "New version will be: $newTag" -ForegroundColor Green
    
    # Check if there are staged changes
    $stagedChanges = git diff --cached --quiet 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✅ Found staged changes, proceeding with commit..." -ForegroundColor Green
        
        # Run tests first
        Write-Host "🧪 Running tests..." -ForegroundColor Cyan
        python run_tests.py
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ All tests passed!" -ForegroundColor Green
            
            # Get list of changed files for commit message
            $changedFiles = git diff --cached --name-only
            $filesList = ($changedFiles | ForEach-Object { "- $_" }) -join "`n"
            
            # Commit the changes
            Write-Host "📝 Committing changes..." -ForegroundColor Cyan
            $commitMessage = @"
Update to version $newTag

$filesList
"@
            git commit -m $commitMessage
            
            # Create the version tag
            Write-Host "🏷️ Creating version tag: $newTag" -ForegroundColor Cyan
            git tag $newTag
            
            Write-Host "✅ Successfully committed and tagged version $newTag" -ForegroundColor Green
            Write-Host "💡 To push: git push origin master && git push origin $newTag" -ForegroundColor Blue
        } else {
            Write-Host "❌ Tests failed! Aborting commit." -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "❌ No staged changes found. Stage your changes first with 'git add'" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
    exit 1
}
