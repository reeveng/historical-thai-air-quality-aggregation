import requests
import json
from datetime import datetime
from pathlib import Path

data_dir = Path("data")
data_dir.mkdir(exist_ok=True)

response = requests.get("http://air4thai.com/forweb/getAQI_JSON.php", timeout=30)
data = response.json()

timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
filepath = data_dir / f"{timestamp}.json"

with open(filepath, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
