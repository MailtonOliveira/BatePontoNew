import os

# Garante que BATEPONTO_SENHA esteja definido para testes,
# evitando que main.py chame sys.exit(1) ao ser importado.
os.environ.setdefault("BATEPONTO_SENHA", "test_pin")
