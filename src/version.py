"""
Version information for FullThumbs application.
Automatically generated from git information.

git commit -m "Release v1.2.0"
git tag v1.2.0
git push origin v1.2.0

python -m src.version
"""

import os, subprocess

def get_git_version() -> str:
	"""
	Get version from git describe or fallback to a default.
	
	Expected tag format: v1.0.0, v1.1.0, etc.
	Returns format like: 1.0.0, 1.0.1-5-g1a2b3c4, or 1.0.0-dev
	"""
	try:
		# Get the directory of this file to ensure we're in the right repo
		repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
		
		# Try git describe first (requires at least one tag)
		result = subprocess.run(
			['git', 'describe', '--tags', '--always', '--dirty=-dirty'],
			cwd=repo_dir,
			capture_output=True,
			text=True,
			check=True
		)
		
		version = result.stdout.strip()
		
		# Remove 'v' prefix if present (v1.0.0 -> 1.0.0)
		if version.startswith('v'):
			version = version[1:]
			
		return version
		
	except (subprocess.CalledProcessError, FileNotFoundError):
		# Fallback: try to get commit hash
		try:
			repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
			result = subprocess.run(
				['git', 'rev-parse', '--short', 'HEAD'],
				cwd=repo_dir,
				capture_output=True,
				text=True,
				check=True
			)
			commit_hash = result.stdout.strip()
			return f"0.0.0-dev-{commit_hash}"
			
		except (subprocess.CalledProcessError, FileNotFoundError):
			# Final fallback
			return "0.0.0-unknown"

def get_build_info() -> dict:
	"""Get detailed build information."""
	try:
		repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
		
		# Get commit hash
		commit_result = subprocess.run(
			['git', 'rev-parse', 'HEAD'],
			cwd=repo_dir,
			capture_output=True,
			text=True,
			check=True
		)
		commit_hash = commit_result.stdout.strip()
		
		# Get commit date
		date_result = subprocess.run(
			['git', 'log', '-1', '--format=%ci'],
			cwd=repo_dir,
			capture_output=True,
			text=True,
			check=True
		)
		commit_date = date_result.stdout.strip()
		
		# Get branch name
		branch_result = subprocess.run(
			['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
			cwd=repo_dir,
			capture_output=True,
			text=True,
			check=True
		)
		branch = branch_result.stdout.strip()
		
		# Check if working directory is dirty
		status_result = subprocess.run(
			['git', 'status', '--porcelain'],
			cwd=repo_dir,
			capture_output=True,
			text=True,
			check=True
		)
		is_dirty = bool(status_result.stdout.strip())
		
		return {
			'version': get_git_version(),
			'commit_hash': commit_hash,
			'commit_hash_short': commit_hash[:7],
			'commit_date': commit_date,
			'branch': branch,
			'is_dirty': is_dirty
		}
		
	except (subprocess.CalledProcessError, FileNotFoundError):
		return {
			'version': get_git_version(),
			'commit_hash': 'unknown',
			'commit_hash_short': 'unknown',
			'commit_date': 'unknown',
			'branch': 'unknown',
			'is_dirty': False
		}

# Cache the version info
_build_info = None

def get_version() -> str:
	"""Get the application version string."""
	global _build_info
	if _build_info is None:
		_build_info = get_build_info()
	return _build_info['version']

def get_version_info() -> dict:
	"""Get complete version information."""
	global _build_info
	if _build_info is None:
		_build_info = get_build_info()
	return _build_info.copy()

# Export the version as a module-level constant
__version__ = get_version()

if __name__ == "__main__":
	# Print version info when run directly
	info = get_version_info()
	print(f"Version: {info['version']}")
	print(f"Commit: {info['commit_hash_short']} ({info['commit_date']})")
	print(f"Branch: {info['branch']}")
	print(f"Dirty: {info['is_dirty']}")
