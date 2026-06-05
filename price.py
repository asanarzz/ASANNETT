name: Update Prices
on:
  schedule:
    - cron: '0 * * * *' # هر یک ساعت اجرا می‌شود
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install requests beautifulsoup4
      - name: Run script
        run: python price.py
      - name: Save results
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add prices.txt
          git commit -m "Update prices"
          git push
