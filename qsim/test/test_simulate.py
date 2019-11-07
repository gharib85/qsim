import numpy as np
import networkx as nx
import unittest

from qsim.qaoa import simulate
from qsim import noise_models
from qsim.qaoa import variational_parameters

# Generate sample graph
g = nx.Graph()

g.add_edge(0, 1, weight=1)
g.add_edge(0, 2, weight=1)
g.add_edge(2, 3, weight=1)
g.add_edge(0, 4, weight=1)
g.add_edge(1, 4, weight=1)
g.add_edge(3, 4, weight=1)
g.add_edge(1, 5, weight=1)
g.add_edge(2, 5, weight=1)
g.add_edge(3, 5, weight=1)

sim = simulate.SimulateQAOA(g, 1, 2, is_ket=False)
sim_ket = simulate.SimulateQAOA(g, 1, 2, is_ket=True)
sim_noisy = simulate.SimulateQAOA(g, 1, 2, is_ket=False)
sim_noisy.noise = []


N = 10
# Initialize in |000000>
psi0 = np.zeros((2 ** N, 1))
psi0[0, 0] = 1

sim.variational_params = [variational_parameters.HamiltonianC(sim.C), variational_parameters.HamiltonianB()]
sim_ket.variational_params = [variational_parameters.HamiltonianC(sim.C), variational_parameters.HamiltonianB()]
sim_noisy.variational_params = [variational_parameters.HamiltonianC(sim.C), variational_parameters.HamiltonianB()]

sim.noise = [noise_models.Noise(), noise_models.Noise()]
sim_ket.noise = [noise_models.Noise(), noise_models.Noise()]
sim_noisy.noise = [noise_models.DepolarizingNoise(.001), noise_models.DepolarizingNoise(.001)]


class TestSimulate(unittest.TestCase):
    def test_variational_grad(self):
        # Test that the calculated objective function and gradients are correct
        # p = 1
        F, Fgrad = sim_ket.variational_grad(np.array([1, 0.5]))
        self.assertTrue(np.abs(F - 1.897011131463) <= 1e-5)
        self.assertTrue(np.all(np.abs(Fgrad - np.array([14.287009047096, -0.796709998210])) <= 1e-5))

        # p = 1 density matrix
        F, Fgrad = sim.variational_grad(np.array([1, 0.5]))

        self.assertTrue(np.abs(F - 1.897011131463) <= 1e-5)
        self.assertTrue(np.all(np.abs(Fgrad - np.array([14.287009047096, -0.796709998210])) <= 1e-5))

        # p = 1 noisy
        F, Fgrad = sim_noisy.variational_grad(np.array([1, 0.5]))
        self.assertTrue(np.abs(F - 1.8869139555669938) <= 1e-5)
        self.assertTrue(np.all(np.abs(Fgrad - np.array([14.21096392, -0.79246937])) <= 1e-5))

        # p = 2
        F, Fgrad = sim_ket.variational_grad(np.array([3, 4, 2, 5]))
        self.assertTrue(np.abs(F + 0.5868545288327245) <= 1e-5)
        self.assertTrue(np.all(np.abs(Fgrad - np.array([3.82877928, 2.10271544, 5.21809702, 4.99717856])) <= 1e-5))

        F, Fgrad = sim.variational_grad(np.array([3, 4, 2, 5]))
        self.assertTrue(np.abs(F + 0.5868545288327245) <= 1e-5)
        self.assertTrue(np.all(np.abs(Fgrad - np.array([3.82877928, 2.10271544, 5.21809702, 4.99717856])) <= 1e-5))

        # p = 3
        params = np.array([-1, 4, 15, 5, -6, 7])
        F, Fgrad = sim.variational_grad(params)
        self.assertTrue(np.abs(F + 1.2541687509598878) <= 1e-5)
        self.assertTrue(np.all(np.abs(Fgrad - np.array([-5.5862387, -3.99650097, -2.43971594, -0.29729297, -3.66785565,
                                                        -3.35531478])) <= 1e-5))

        F, Fgrad = sim.variational_grad(params)
        self.assertTrue(np.abs(F + 1.2541687509598878) <= 1e-5)
        self.assertTrue(np.all(np.abs(Fgrad - np.array([-5.5862387, -3.99650097, -2.43971594, -0.29729297, -3.66785565,
                                                        -3.35531478])) <= 1e-5))

    def test_run(self):
        sim.p = 1
        sim_noisy.p = 1
        # p = 1 density matrix
        self.assertAlmostEqual(sim.run([1, .5]), 1.897011131463)
        self.assertAlmostEqual(sim_ket.run([1, .5]), 1.897011131463)

        # See how things look with noise
        self.assertAlmostEqual(sim_noisy.run([1, .5]), 1.8869139555669938)

        # Higher depth circuit
        params = np.array([-1, 4, 15, 5, -6, 7])
        F, Fgrad = sim.variational_grad(params)
        self.assertTrue(np.abs(F + 1.2541687509598878) <= 1e-5)
        self.assertTrue(np.all(np.abs(Fgrad - np.array([-5.5862387, -3.99650097, -2.43971594, -0.29729297, -3.66785565,
                                                        -3.35531478])) <= 1e-5))

    def test_find_optimal_params(self):
        sim.p = 3
        sim_noisy.p = 3
        print('Noiseless:')
        sim.find_parameters_minimize()
        print('Noisy:')
        sim_noisy.find_parameters_minimize()

if __name__ == '__main__':
    unittest.main()