from powertower import PowerTower

# Different heights
assert PowerTower(0, 3) < PowerTower(1, 2)    # 3 < 100
assert PowerTower(1, 2) < PowerTower(2, 1)    # 100 < 10^10
assert PowerTower(2, 0) < PowerTower(1, 100)  # 10 < 10^100

# Equivalent values in different forms
assert PowerTower(0, 10) == PowerTower(1, 1)  # 10 == 10^1
assert PowerTower(0, 1) == PowerTower(1, 0)   # 1 == 10^0

# All six comparison operators
a = PowerTower(1, 3)
b = PowerTower(1, 4)

assert a < b
assert a <= b
assert b > a
assert b >= a
assert a == PowerTower(1, 3)
assert a != b

print("PowerTower edge-case tests passed!")