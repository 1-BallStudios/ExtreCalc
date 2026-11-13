from biginteger import BigInt

dict=[]

temp = BigInt("1")
for i in range(1000):
    temp *= BigInt(str(i))+BigInt("1")
    if i%20 == 0:
        dict.append(str(temp))
print(str(dict))