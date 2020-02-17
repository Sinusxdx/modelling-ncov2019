from scipy.stats import poisson


def kernel(lambda_fcn, T, gamma, x):
    return poisson.rvs(gamma * T * lambda_fcn(x), size=1)

