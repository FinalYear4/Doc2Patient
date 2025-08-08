# run.py
from main import app

if __name__ == "__main__":
    app.run(debug=True)
```    *Now, when you run `python run.py` locally, it will correctly start through `main.py`, ensuring the monkey patch is applied even during development.*