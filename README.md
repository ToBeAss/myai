# myai
My personal AI assistant

## Installation Instructions

### Prerequisites:

- *[List required software or dependencies, e.g., Node.js, Java, Docker, etc.]*
- Python 3.12.9

### Steps:
1. **Clone the repository**
   ```bash
   git clone https://github.com/ToBeAss/myai.git
   ```
2. **Create a virtual environment**
   > Creating a Python virtual environment allows you to manage dependencies separately for different projects, preventing conflicts and maintaining cleaner setups. [Real Python, 2024](https://realpython.com/python-virtual-environments-a-primer/)

    ```bash
    python -m venv venv
    ```
    > For **macOS** you may need to use `python3 -m venv venv`.
3. **Activate the virtual environment**

    * **Windows (Command Prompt)**
        ```bash
        venv\Scripts\activate
        ```
    * **macOS**
        ```bash
        source venv/bin/activate
        ```
4. **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```
    > For **macOS** you may need to use `pip3 install -r requirements.txt`.
5. **Create the `.env` file**
    
    Copy the `.env.example` file and rename it `.env`:

    * **Windows (Command Prompt)**
        ```bash
        copy .env.example .env
        ```
    * **macOS**
        ```bash
        cp .env.example .env
        ```
    Open the `.env` file and insert the API keys.

> [!WARNING]
> The `.env` file is used to store sensitive information like API keys and database credentials securely. Make sure not to commit it to version control by adding `.env` to your `.gitignore` file.

## Environment Management
* **Deactivate the virtual environment** (when done)
    ```bash
    deactivate
    ```
* **(Optional) Export Installed Packages**
    
    If you add new dependencies, update the `requirements.txt`:
    ```bash
    pip freeze > requirements.txt
    ```