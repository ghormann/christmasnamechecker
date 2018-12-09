import re

def clean_name(name):
    name = name.strip().upper()
    return re.sub('\s+', '', name)

class NameValidator:
    """Once loaded with a file of first names, it will state if a given first name is valid or not"""
    def __init__(self, filename):
        self.names = {}
        with open(filename, 'r') as f:
            content = f.readlines();
            for name in content:
                name = clean_name(name)
                self.names[name] = 1
        print("Loaded ", len(self.names))

    def addNames(self, filename):
        with open(filename, 'r') as f:
            content = f.readlines();
            for name in content:
                name = clean_name(name)
                self.names[name] = 1
        print("Loaded ", len(self.names))
    def isValid(self, name):
        name = clean_name(name)
        if name in self.names:
            return True
        return False

if __name__ == "__main__":
    db = NameValidator("data/all_names.txt")
    db.addNames("data/custom.txt")
    print(db.isValid('Heidi'))
    print(db.isValid('Mom'))
    
