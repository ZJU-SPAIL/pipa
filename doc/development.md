## PIPA Development Guidelines

*Enforced by Black Linter for Python Code*  


### **1. Code Quality Standards**  
**1.1 Remove Redundant Content**  
- **Unused Comments**: Delete obsolete or irrelevant comments (e.g., `# TODO: fix this later` if unresolved).  
- **Unused Files**: Remove files no longer referenced in the project.  

**1.2 Avoid Magic Numbers**  
- Replace hardcoded numeric literals with **named constants** or **enum values** for clarity.  
  ```python  
  # ❌ Bad: Magic numbers  
  if account == 1:  
      ...  
  elif account == 2:  
      ...  

  # ✅ Good: Semantic constants  
  ACCOUNT_TYPE_ADMIN = 1  
  ACCOUNT_TYPE_USER = 2  

  if account == ACCOUNT_TYPE_ADMIN:  
      ...  
  ```  

**1.3 Eliminate Hardcoding**  
- **Configuration Isolation**: Externalize sensitive or environment-specific data (e.g., DB credentials, URLs) into configuration files or environment variables.  
  ```yaml  
  # ❌ Bad: Hardcoded credentials  
  datasource:  
    url: jdbc:mysql://192.168.1.1:3306/demo  
    username: root  
    password: 123456  

  # ✅ Good: Environment variables  
  datasource:  
    url: jdbc:mysql://${DB_HOST}:${DB_PORT}/demo  
    username: ${DB_USERNAME}  
    password: ${DB_PASSWORD}  
  ```  

**1.4 Refactor Legacy Code**  
- **Avoid Duplication**: Do not create redundant functions like `get()`, `get1()`, `get2()` for the same purpose. Use polymorphism or refactoring.  
  ```python  
  # ❌ Bad: Duplicated logic  
  def get():  
      ...  
  def get1():  
      ...  

  # ✅ Good: Unified function  
  def retrieve_data(source: str) -> dict:  
      ...  
  ```  


### **2. Naming Conventions**  
**2.1 Domain/URL/Code Repository**  
- **Semantic and Consistent**: Use clear terms (e.g., `api`, `admin`, `docs`).  
- **Hyphens Over Underscores**: Prefer hyphens for readability (e.g., `https://api.pipa.com/v1/users`).  
- **No Uppercase or Pinyin**: Avoid uppercase letters and non-semantic pinyin (e.g., `https://www.apple.com/shop/buy-iphone/iphone-15-pro`).  


### **3. Git Workflow**  
**3.1 Commit Practices**  
- **Atomic Commits**: Each commit should address a single logical change.  
- **Commitizen for Semantics**: Use `cz c` for standardized commit messages (e.g., `feat: add user authentication`).  
  ```bash  
  pip install commitizen  
  git add .  
  cz c  
  ```  

**3.2 Branching & Merging**  
- **Small, Frequent Merges**: Use CI/CD pipelines for rapid feedback.  
- **Branch Naming**: Align with issue IDs (e.g., `feature/123-add-payment`).  
- **Rebase Over Merge**:  
  - Use `git rebase` to maintain a linear history.  
  - Delete temporary branches immediately after merging.  
  - **Squash Commits**: For multi-step features, use `--squash` to condense history.  

**3.3 Prohibited Actions**  
- **No Direct Main Branch Pushes**: All changes must go through MR/PR reviews.  
- **No History Rewriting**: Use `git revert` for rollbacks, not `git reset` or `--force`.  


### **4. Configuration & Dependencies**  
**4.1 .gitignore Rules**  
- Exclude build artifacts, dependencies, and IDE files:  
  ```gitignore  
  /node_modules  
  /vendor  
  *.pyc  
  .env  
  ```  

**4.2 External Resources**  
- **CDN for Static Assets**: Avoid bundling third-party libraries (e.g., Bootstrap).  
- **Artifact Repositories**: Store compiled files in a CI/CD artifact registry (e.g., `index.u98ashj.css`).  


### **5. Versioning**  
**5.1 Semantic Versioning (SemVer)**  
- **Format**: `MAJOR.MINOR.PATCH`  
  - **MAJOR**: Breaking changes (e.g., API deprecation).  
  - **MINOR**: Backward-compatible features (e.g., new endpoints).  
  - **PATCH**: Bug fixes (e.g., security patches).  


### **6. Black Linter Configuration**  
**6.1 Enforce Formatting**  
- **Line Length**: 88 characters (default in Black).  
- **Quotes**: Use double quotes (`"`) consistently.  
- **Imports**: Sort imports alphabetically with `isort`.  

**6.2 Integration**  
- Add to `pyproject.toml`:  
  ```toml  
  [tool.black]  
  line-length = 88  
  target-version = ['py310']  
  ```  

### **7. Compliance & Enforcement**  
- **Pre-commit Hooks**: Automate Black formatting and linter checks.  
- **CI/CD Pipeline**: Fail builds on style violations or unformatted code.  
- **Code Reviews**: Require MR/PR approvals for all changes.  

