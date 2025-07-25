# Personalized B2B Outreach Automation Project

This project automates the creation of personalized outreach messages for potential leads using enriched company data. It integrates with the Gemini API for text generation and the Apollo API for lead fetching.

# Complete flow chart of the code
![Flow Chart](https://github.com/vishwashdark/automation_final/blob/main/flow%20chart%20for%20code.png)

## Project Structure

- **`test.ipynb`**: Jupyter Notebook for testing and generating outreach messages.
- **`readme.md`**: Project documentation.
- **`requirements.txt`**: List of required dependencies.

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   ```
2. **Navigate to the project directory:**
   ```bash
   cd automation
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Manually add the gemini API key in `test.ipynb`:**
   Open `test1.py` and add the gemini api in get_gemini_api_key() function.


5. **Run the Python script:**
   ```bash
   python test1.py
   ```

## API Key Setup

- **Gemini API Key:**  
  Set the `GEMINI_API_KEY` variable in `test.ipynb` to your Gemini API key.

- **Apollo API Key:**  
  Set the `APOLLO_API_KEY` variable in `test1.py` to your Apollo API key.

## Usage
1. **Run the Python script:**
   ```bash
   python test1.py
   ```
test1.py --size '50-400' --industry 'software' --location 'United States' {optional location filter}

