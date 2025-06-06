

class nonNumpyPolynomial:
    def __init__(self, coefficients):
        self.coefficients=coefficients

    def get_coefficients(self):
        return self.coefficients.copy()

    def __call__(self, x):
        y=0
        for i in range(len(self.coefficients)):
            y+= self.coefficients[i]*(x**i)
        return y 