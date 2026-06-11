.PHONY: install demo multi-turn notebook qr clean

install:
	pip install -r requirements.txt

demo:
	python3 demo_gcg.py

multi-turn:
	python3 demo_multi_turn.py

notebook:
	jupyter notebook prompt_injection_demo.ipynb

qr:
	python3 -c "import qrcode; qr = qrcode.make('https://github.com/joaopedropassostocantins/PIKACHU'); qr.save('pikachu_qr.png'); print('QR saved to pikachu_qr.png')"

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ipynb_checkpoints" -exec rm -rf {} + 2>/dev/null || true
