import typing

def string_to_int(string) -> int:
    if string[0] == "-":
        return -1 * int(string[1:])
    else:
        return int(string)

class Checking:
    def __init__(self, *data):
        self.data = list(data)

    def clear_scopes(self) -> str:
        if type(self.data) == list:
            self.data = str(self.data[0])

        found_scopes = ""
        if self.data[0] in ('(', '[', '{'):
            found_scopes = self.data[0]
            self.data = self.data[1:]

        if self.data[-1] in (')', ']', '}'):
            found_scopes += self.data[-1]
            self.data = self.data[:-1]

        return found_scopes

    def split_str_to_list(self) -> None:
        self.data = self.data.replace(',', '\n').replace(';', '\n').splitlines()
        for i in range(len(self.data)):
            self.data[i] = self.data[i].strip()

    def list_to_int(self, start = 0, end = -1) -> None:
        if end == -1:
            end = len(self.data)
        for i in range(start, end):
            self.data[i] = string_to_int(self.data[i])
