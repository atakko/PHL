class Player:
    def __init__(self, id, name, nationality):
        self.id = id
        self.name = name
        self.nationalty = nationality

    def __str__(self):
        return f"{self.id} {self.nationalty} {self.name}"