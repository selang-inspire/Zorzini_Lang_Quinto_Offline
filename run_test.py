#concept of returning a variable in case there is any error in the code

class hex:
    error_report = 0

    def t(error_report):
        try:
            1/0
        except:
            error_report = 1
            return error_report

variable = hex()
print(variable.error_report)
try:
    variable.error_report=variable.t()
    print(variable.error_report)
    if variable.error_report == 1:
        raise Exception
except :
    print(variable.error_report)
    print('error detected')