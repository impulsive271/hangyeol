# Hangyeol (한결)

**한국어** | [English](./README.en.md)

A web application for Korean text vocabulary level analysis and sentence generation.

## Key Features

1. **Vocabulary Level Analysis**
   - Analyzes the vocabulary level of Korean sentences and texts in real time.
   - Visualizes the distribution of vocabulary difficulty across beginner, intermediate, and advanced levels.

2. **Custom Example Generation**
   - Generates example sentences tailored to learner levels based on specific proficiency levels (e.g., beginner, intermediate) and keywords.
   - Provides natural sentences powered by Google Gemini AI.

3. **Automatic Quiz Generation**
   - Automatically generates various types of questions — such as fill-in-the-blank and meaning matching — based on given passages.
   - Reduces the time for textbook developers and teachers to create learning materials.


## Prerequisites

- Python 3.8 or higher
- Google Gemini API Key (required for generation features)

> **⚠️ Note (Without API Key)**
> The application runs and the basic 'Vocabulary Level Analysis' feature works without a Google API Key.
> However, the following AI-dependent features will be unavailable:
> - Context-based disambiguation of homonyms during vocabulary analysis (defaults will be used)
> - Custom example generation
> - Automatic quiz generation

## Installation & Setup

Follow these steps to clone the repository and run the application.

### 1. Clone the Repository

```bash
git clone https://github.com/impulsive271/hangyeol.git
cd hangyeol
```

### 2. Set Up Virtual Environment (Recommended)

```bash
# macOS/Linux
python -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Environment Variables

Create a `.env` file in the project root directory and add the following.
You can obtain a `GOOGLE_API_KEY` from [Google AI Studio](https://aistudio.google.com/).

```bash
# Create .env file
echo "GOOGLE_API_KEY=your_api_key_here" > .env
```

Or create the `.env` file manually with the following content:
```
GOOGLE_API_KEY=your_api_key_here
```

### 5. Run the Application

```bash
python app.py
```

### 6. Access

Open your browser and navigate to:
http://127.0.0.1:5000

## Citation

[![DOI](https://img.shields.io/badge/DOI-10.16933/sfle.2026.40.1.49-blue.svg)](https://doi.org/10.16933/sfle.2026.40.1.49)

- Kim, T., & You, H. J. (2026). Development of a web application for Korean text analysis and generation based on vocabulary profile. *Studies in Foreign Language Education*, *40*(1), 49–80. https://doi.org/10.16933/sfle.2026.40.1.49

```bibtex
@article{kim2026hangyeol,
  title     = {Development of a Web Application for Korean Text Analysis and Generation Based on Vocabulary Profile},
  author    = {Kim, Taehyun and You, Hyun Jo},
  journal   = {Studies in Foreign Language Education},
  volume    = {40},
  number    = {1},
  pages     = {49--80},
  year      = {2026},
  doi       = {10.16933/sfle.2026.40.1.49}
}
```
