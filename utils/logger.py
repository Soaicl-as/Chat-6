class Logger:
    def __init__(self):
        self.logs = []

    def log(self, msg):
        print(msg)
        self.logs.append(msg)
        if len(self.logs) > 100:
            self.logs.pop(0)

    def get_logs(self):
        return self.logs

    def clear(self):
        self.logs = []
