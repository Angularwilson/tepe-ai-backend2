# testons = [1,2]
# match testons :
#     case [x,y]:
#         print(f"on a deux element {x} et {y}")
#     case _:
#         print("on a autre chose")


voitures =['audi','bmw','mercedes']
filles =['aline','deborah','sarah']
choix = input("choisisser le nom d'une fille ou d'une voiture :\n")

match choix:
    case v if v in voitures:
        print(f" {v} est dans la liste de voiture ")
    case f if f in filles:
        print(f" {f} est dans la liste c'est bien")
    

