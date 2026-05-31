---
name: pr-review-merge
description: Review and merge pull requests with CI checks and OpenCode review validation
---

# PR Review and Merge Workflow

This skill handles the complete PR review and merge workflow, including:
1. CI check validation
2. OpenCode review comment analysis
3. Conflict resolution
4. Automated merging

## Workflow Steps

### 1. List Open PRs
```bash
gh pr list
```

### 2. Check PR Status
For each PR, check:
- CI status: `gh pr checks <pr-number>`
- Review comments: `gh pr view <pr-number> --json comments`
- OpenCode review workflow logs: `gh run view <run-id> --log`

### 3. Validate OpenCode Reviews
Check for OpenCode review comments in:
- PR comments from `github-actions` bot
- Workflow run logs from `opencode-review` workflow

Look for review feedback patterns:
- Code quality issues
- Potential bugs
- Suggested improvements
- Security concerns

### 4. Handle Issues
If OpenCode review or CI identifies issues:
- Checkout the PR branch
- Fix identified issues
- Commit and push changes
- Wait for CI to re-run

### 5. Resolve Conflicts
If PR has merge conflicts:
```bash
gh pr checkout <pr-number>
git fetch origin main
git rebase origin/main
# Resolve conflicts
git add <resolved-files>
git rebase --continue
git push origin <branch-name> --force
```

### 6. Merge PR
Once all checks pass and no review issues:
```bash
gh pr merge <pr-number> --squash --delete-branch
```

## OpenCode Review Check

The OpenCode review workflow (`.github/workflows/opencode-review.yml`) runs on PRs but skips bot-created PRs.

To check for OpenCode feedback:
1. Get workflow run ID from `gh pr checks <pr-number>`
2. View logs: `gh run view <run-id> --log`
3. Look for review output in the logs
4. Check PR comments for any posted feedback

## Priority Order

Process PRs in this order:
1. PRs with passing CI and no review issues
2. PRs with passing CI but merge conflicts
3. PRs with failing CI (investigate and fix)
4. PRs with OpenCode review concerns (address feedback)

## Example Usage

```bash
# List all open PRs
gh pr list

# Check specific PR
gh pr view 50
gh pr checks 50

# Check for OpenCode review
gh pr view 50 --json comments --jq '.comments[] | select(.author.login | contains("github-actions"))'

# Merge if ready
gh pr merge 50 --squash --delete-branch
```
