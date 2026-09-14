# 1. പൈത്തൺ 3.11 ബേസ് ഇമേജ് ഉപയോഗിക്കുന്നു
FROM python:3.11-slim

# 2. വർക്കിങ് ഡയറക്ടറി സെറ്റ് ചെയ്യുന്നു
WORKDIR /app

# 3. സിസ്റ്റം അപ്ഡേറ്റുകളും Pyrogram-ന്റെ സ്പീഡ് കൂട്ടാനുള്ള GCC ടൂളുകളും ഇൻസ്റ്റാൾ ചെയ്യുന്നു
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    & \
    rm -rf /var/lib/apt/lists/*

# 4. requirements.txt കോപ്പി ചെയ്ത് ലൈബ്രറികൾ ഇൻസ്റ്റാൾ ചെയ്യുന്നു
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. ബാക്കിയുള്ള എല്ലാ കോഡുകളും ഫോൾഡറുകളും കോപ്പി ചെയ്യുന്നു
COPY . .

# 6. ബോട്ട് റൺ ചെയ്യാനുള്ള ഫൈനൽ കമാൻഡ്
CMD ["python", "bot.py"]

