# ClubHub – Git & GitHub Workflow Guide

This document explains how team members should authenticate with GitHub, clone the repository, and follow best practices when implementing features.

---

# Prerequisites

**This document assumes you have the following prerequisites installed on your system:**

* **Git** – distributed version control system used to track code changes
* **GitHub CLI (`gh`)** – command-line tool used to interact with GitHub
* A **GitHub account**
* Access permissions to the ClubHub repository

If any of these are missing, install them before continuing.

---

# Repository Remote

The repository used in this project:

```text
git@github.com:kwanele-Cyber/clubhub.git
```

This repository uses **SSH authentication**, which allows developers to securely push and pull code without entering credentials each time.

---

# 1. Verify Installed Tools

Check that Git and GitHub CLI are installed.

```bash
git --version
gh --version
```

### What this does

* `git --version` confirms that Git is installed and accessible.
* `gh --version` confirms that GitHub CLI is installed and working.

If both commands return version numbers, your environment is ready.

---

# 2. Authenticate with GitHub

Authenticate your local machine with GitHub using the GitHub CLI.

```bash
gh auth login
```

When prompted:

1. Select **GitHub.com**
2. Select **SSH**
3. Authenticate via **browser**

### What this does

This command:

* Connects your local machine to your GitHub account
* Configures authentication for Git operations
* Automatically generates an **SSH key if one does not exist**
* Uploads the key to GitHub
* Enables secure push and pull operations

Verify authentication:

```bash
gh auth status
```

### What this does

Displays the GitHub account currently authenticated on your system.

---

# 3. Clone the Repository

Clone the project to your local machine.

```bash
git clone git@github.com:kwanele-Cyber/clubhub.git
```

Move into the project directory:

```bash
cd clubhub
```

### What this does

`git clone`:

* Downloads the **entire repository**
* Includes all commits and project history
* Creates a local working directory
* Connects your local repository to a remote called **origin**

Alternative using GitHub CLI:

```bash
gh repo clone kwanele-Cyber/clubhub -- --ssh
```

---

# 4. Verify Remote Configuration

Confirm the repository remote is configured correctly.

```bash
git remote -v
```

Expected output:

```
origin  git@github.com:kwanele-Cyber/clubhub.git (fetch)
origin  git@github.com:kwanele-Cyber/clubhub.git (push)
```

### What this does

* Lists the remote repositories connected to your local project
* `origin` refers to the repository you cloned from
* `fetch` is used for pulling updates
* `push` is used for uploading your commits

---

# 5. Synchronize with the Main Branch

Before starting work, update your local repository.

```bash
git checkout main
git pull origin main
```

### What this does

`git checkout main`

* Switches your working directory to the **main branch**

`git pull origin main`

* Downloads the latest changes from GitHub
* Merges them into your local branch
* Ensures you are working on the latest codebase

---

# 6. Branching Strategy

Never work directly on the **main** branch.

Instead create a feature branch.

```bash
git checkout -b feature/user-authentication
```

### What this does

`git checkout -b`:

* Creates a new branch
* Immediately switches to that branch
* Isolates your work from the main codebase

### Branch Naming Convention

```
feature/<feature-name>
bugfix/<bug-name>
chore/<maintenance-task>
```

Examples:

```
feature/event-registration
bugfix/login-validation
chore/update-dependencies
```

---

# 7. Implementing a Feature

## Step 1 — Update Main

```bash
git checkout main
git pull origin main
```

### What this does

Ensures your feature branch starts from the **latest version of the project**.

---

## Step 2 — Create Feature Branch

```bash
git checkout -b feature/add-login-endpoint
```

### What this does

Creates a separate branch for your work so it does not affect other developers.

---

## Step 3 — Implement Changes

Edit the project files as needed.

Git will automatically detect file modifications.

---

## Step 4 — Stage Changes

```bash
git add .
```

### What this does

Adds modified files to the **staging area**, preparing them for a commit.

Alternative for specific files:

```bash
git add templates/createEvent.html
git add app.py
```

---

## Step 5 — Commit Changes

```bash
git commit -m "feat: add login endpoint"
```

### What this does

A **commit** creates a snapshot of your changes and saves it in the project history.

Each commit should represent a **logical unit of work**.

---

# 8. Commit Message Best Practices

Use **Conventional Commit format**.

Format:

```
type: description
```

Examples:

```
feat: add club registration endpoint
fix: resolve login validation bug
docs: update README
refactor: simplify event service
test: add login endpoint tests
chore: update dependencies
```

### Why this matters

* Keeps commit history readable
* Helps with automated changelog generation
* Makes code reviews easier

---

# 9. Push Your Branch

Upload your branch to GitHub.

```bash
git push origin feature/add-login-endpoint
```

### What this does

`git push`:

* Sends your local commits to GitHub
* Creates the branch on the remote repository
* Makes your work visible to other developers

---

# 10. Create a Pull Request (PR)

Create a Pull Request using the GitHub CLI.

```bash
gh pr create
```

### What a Pull Request is

A **Pull Request (PR)** is a request to merge your branch into another branch (usually `main`).

It allows team members to:

* Review your code
* Suggest improvements
* Discuss changes before merging

### What this command does

* Creates a PR on GitHub
* Links your branch with the target branch
* Opens a review process

Example PR description:

```
Summary:
Adds login endpoint for user authentication.

Changes:
- Added login controller
- Added JWT authentication service
- Added validation middleware
```

---

# 11. Updating Your Branch with Main

If the main branch changes while you're working:

```bash
git checkout main
git pull origin main

git checkout feature/add-login-endpoint
git merge main
```

### What this does

* Downloads the latest updates from the main branch
* Merges those updates into your feature branch
* Reduces the chance of merge conflicts later

---

# 12. After a Pull Request is Merged

Once your PR is merged, clean up your branches.

Delete local branch:

```bash
git branch -d feature/add-login-endpoint
```

### What this does

Removes the branch from your local repository.

Delete remote branch:

```bash
git push origin --delete feature/add-login-endpoint
```

### What this does

Removes the branch from GitHub to keep the repository organized.

---

# 13. Typical Developer Workflow

```
git checkout main
git pull origin main
git checkout -b feature/my-feature

# implement feature

git add .
git commit -m "feat: add new feature"

git push origin feature/my-feature

gh pr create
```

---

# Key Rules for the Team

* Always **clone using SSH**
* Never push directly to **main**
* Always work in **feature branches**
* Every change must go through a **Pull Request**
* Write **clear and descriptive commit messages**
* Pull the latest changes before starting work

---
