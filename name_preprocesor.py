import csv
import glob

class NameParser:
    """Parses all years of data from https://www.ssa.gov/oact/babynames/limits.html to get a uniqe set of 
    English first names
    """

    def __init__(self):
        self.data  = {}

    def process_file(self, filename):
        with open(filename, 'r') as f:
            reader = csv.reader(f, dialect='excel', delimiter=',')
            for row in reader:
                firstname = (row[0]).upper()
                self.data[firstname] = 1

    def save(self, filename):
        print(len(self.data))
        with open(filename, 'w+') as f:
            for name in sorted(self.data.keys()):
                f.write(name)
                f.write("\n")
        print("Saved to ", filename)

    def process_dir(self, dir):
        search = dir + "/*txt"
        print("Searching directory: ", search)
        for f in glob.glob(search):
            print (f)
            self.process_file(f)

if __name__ == "__main__":
    parser = NameParser()
    parser.process_dir("data/source")
    parser.save("data/all_names.txt")