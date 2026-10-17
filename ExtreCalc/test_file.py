from expantanum import ExpantaNum

def test_expantanum_operations():
    assert ExpantaNum(7).cmp(ExpantaNum(9)) == -1
    assert ExpantaNum(9).cmp(ExpantaNum(9)) == 0
    assert ExpantaNum(9).cmp(ExpantaNum(7)) == 1

    assert ExpantaNum(2).pow(10).to_float() == 1024
    assert ExpantaNum.hyper(2, 1, 3).to_float() == 5
    assert ExpantaNum.hyper(2, 2, 3).to_float() == 6
    assert ExpantaNum.hyper(2, 3, 3).to_float() == 8

    assert ExpantaNum.tetr(2, 3).to_float() == 16
    assert ExpantaNum.pent(2, 2).to_float() == 4

    print("All initial ExpantaNum operation tests passed!")


if __name__ == "__main__":
    test_expantanum_operations()