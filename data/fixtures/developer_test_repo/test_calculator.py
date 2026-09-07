from calculator import calculate, multiply

def test_calculate():
    assert calculate(2, 3) == 5

def test_multiply():
    assert multiply(3, 4) == 12
