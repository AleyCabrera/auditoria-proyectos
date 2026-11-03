# Bugs deliberados: comparación insegura, uso de eval
import hashlib


def check_password(password, stored_hash):
    # Comparación no constante en el tiempo
    return hashlib.md5(password.encode()).hexdigest() == stored_hash


def run_formula(expr):
    # eval sobre input
    return eval(expr)