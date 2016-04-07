from math import pi, fabs
from random import random

class Circle:

    POINTS = 10

    def __init__(self, radius):
        self.radius = radius
        self.area = radius*radius * pi

    def monte_carlo(self, iteration):
        num_area = 0

        for _ in range(Circle.POINTS**iteration):
            if (self.radius*random())**2 + (self.radius*random())**2 < self.radius**2:
                num_area += self.radius**2

        # divide by Circle.POINTS to get the probability and multiply by 4 because we only integrate one quadrant
        num_area = num_area/(Circle.POINTS**iteration)*4
        error = fabs(self.area-num_area)/num_area

        print("Points: 10^" + str(iteration) + " " + str(self.area) + " - " + str(num_area) + " - Error: " + str(error*100))


if __name__==  "__main__":
    circle = Circle(4)

    iteration = 1
    while True:
        circle.monte_carlo(iteration)
        iteration += 1

