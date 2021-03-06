import numpy as np
from qsim.evolution import lindblad_operators, hamiltonian
from qsim import lindblad_master_equation
from qsim import tools
import matplotlib.pyplot as plt
import networkx as nx
from qsim.tools import tools
from qsim.codes import qubit
from qsim.codes.quantum_state import State
from scipy.sparse import csr_matrix
from qsim.graph_algorithms.graph import Graph

N = 3


class MISLoweringJumpOperator(object):
    """Jump operators which enforce the independent set constraint."""

    def __init__(self, graph: nx.Graph, rate):
        super().__init__(jump_operators=[np.array([[0, 0, 0, 0], [1, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]),
                                         np.array([[0, 0, 0, 0], [0, 0, 0, 0], [1, 0, 0, 0], [0, 0, 0, 0]]),
                                         np.array([[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [1, 0, 0, 0]])],
                         weights=rate)
        # Construct the right jump_operators operators
        self.code = qubit
        self.graph = graph
        self.N = self.graph.number_of_nodes()
        jump_operators = []

        for (i, j) in graph.edges:
            for p in range(len(self.jump_operators)):
                temp = tools.tensor_product([self.jump_operators[p], tools.identity(self.N - 2)])
                temp = np.reshape(temp, 2 * np.ones(2 * self.N, dtype=int))
                temp = np.moveaxis(temp, [0, 1, self.N, self.N + 1], [i, j, self.N + i, self.N + j])
                temp = np.reshape(temp, (2 ** self.N, 2 ** self.N))
                jump_operators.append(temp)
        self.jump_operators = jump_operators

    def liouvillian(self, s, i):
        a = np.zeros(s.shape)
        a = a + self.weights * (self.jump_operators[i] @ s @ self.jump_operators[i].T -
                                1 / 2 * s @ self.jump_operators[i].conj().T @ self.jump_operators[i] -
                                1 / 2 * self.jump_operators[i].conj().T @ self.jump_operators[i] @ s)
        return a

    def all_qubit_liouvillian(self, s):
        a = np.zeros(s.shape)
        for i in range(len(self.jump_operators)):
            a = a + self.liouvillian(s, i)
        return a


def IS_projector(G):
    global N
    rr = np.array([[1, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
    C = np.identity(2 ** N)
    for i, j in G.edges:
        temp = tools.tensor_product([rr, tools.identity(N-2)])
        temp = np.reshape(temp, 2*np.ones(2*N, dtype=int))
        temp = np.moveaxis(temp, [0, 1, N, N+1], [i, j, N+i, N+j])
        temp = np.reshape(temp, (2**N, 2**N))
        C = C @ (np.identity(2**N) - temp)
    return C

def cost_function(G, penalty):
    global N
    sigma_plus = np.array([1, 0])
    rr = np.array([[1, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
    C = np.zeros([2 ** N])
    myeye = lambda n: np.ones(np.asarray(sigma_plus.shape[0]) ** n)

    for i, j in G.edges:
        temp = tools.tensor_product([rr, tools.identity(N-2)])
        temp = np.reshape(temp, 2*np.ones(2*N, dtype=int))
        temp = np.moveaxis(temp, [0, 1, N, N+1], [i, j, N+i, N+j])
        temp = np.reshape(temp, (2**N, 2**N))
        C = C + np.diagonal(temp) * penalty * -1
    for c in G.nodes:
        C = C + tools.tensor_product([myeye(c), sigma_plus, myeye(N - c - 1)])
    return C

rydberg_noise_rate = 10
G = nx.Graph()

G.add_edge(0, 1, weight=rydberg_noise_rate)
#G.add_edge(2, 3, weight=rydberg_noise_rate)
G.add_edge(0, 2, weight=rydberg_noise_rate)
G.add_edge(1, 2, weight=rydberg_noise_rate)
zero = np.zeros([1, 2 ** N], dtype = np.complex128)
zero[-1,-1] = 1
zero = zero.T
zero = tools.outer_product(zero, zero)
#plot.draw_graph(G)
# Goal: numerically integrate master equation with (1) spontaneous emission and (2) IS constraint evolution
# with Hb hamiltonian
p = 2
spacing = 10
#se_noise_rate = 0.01
#se_noise = jump_operators.SpontaneousEmission(se_noise_rate)
rydberg_noise = MISLoweringJumpOperator(G, rydberg_noise_rate)
hb_x = hamiltonian.HamiltonianDriver(pauli ='X')
hb_y = hamiltonian.HamiltonianDriver(pauli ='Y')
hb_z = hamiltonian.HamiltonianDriver(pauli ='Z')
hMIS = hamiltonian.HamiltonianMIS(G, blockade_energy=rydberg_noise_rate)
C = cost_function(G, rydberg_noise_rate)
C = C/np.max(C)
is_proj = IS_projector(G)
s = zero
costs = np.zeros((spacing, spacing))
probabilities = np.zeros((spacing ** p, 2**N))
m = 0
for i in np.linspace(0, 2 * np.pi/np.sqrt(3), spacing):
    n = 0
    for l in np.linspace(0, 2 * np.pi/np.sqrt(3), spacing):
        print(m, n, i, l)
        s = zero
        me = lindblad_master_equation.MasterEquation(hamiltonians = [hb_x, hb_y], jump_operators = [rydberg_noise])
        def f_MIS(state, t):
            # hbar is set to zero
            global i
            res = np.zeros(state.shape)
            res = res + -1j * (
                hMIS.left_multiply(state, is_ket=False) - hMIS.right_multiply(state, is_ket=False))
            if t<i:
                res = res + -1j * (me.hamiltonians[0].left_multiply(state, is_ket=False) - me.hamiltonians[0].right_multiply(state, is_ket=False))
            else:
                res = res + -1j * (me.hamiltonians[1].left_multiply(state, is_ket=False) - me.hamiltonians[1].right_multiply(state, is_ket=False))
            return res
        def f_EIT(state, t):
            # hbar is set to zero
            global i
            res = np.zeros(state.shape)
            res = res + -1j/2 * (
                    hb_z.left_multiply(state, is_ket=False) - hb_z.right_multiply(state, is_ket=False))
            if t<i:
                res = res + -1j * (me.hamiltonians[0].left_multiply(state, is_ket=False) - me.hamiltonians[0].right_multiply(state, is_ket=False))
            else:
                res = res + -1j * (me.hamiltonians[1].left_multiply(state, is_ket=False) - me.hamiltonians[1].right_multiply(state, is_ket=False))
            for noise_model in me.jump_operators:
                res = res + noise_model.all_qubit_liouvillian(state)
            return res
        def f_var_diss(state, t):
            # hbar is set to zero
            global i
            res = np.zeros(state.shape)
            if t<i:
                res = res + -1j / 2 * (
                        hb_z.left_multiply(state, is_ket=False) - hb_z.right_multiply(state, is_ket=False))
                res = res + -1j * (me.hamiltonians[0].left_multiply(state, overwrite=False) - me.hamiltonians[0].right_multiply(state, overwrite=False))
            if t>i+.1:
                res = res + -1j / 2 * (
                        hb_z.left_multiply(state, is_ket=False) - hb_z.right_multiply(state, is_ket=False))
                res = res + -1j * (
                            me.hamiltonians[1].left_multiply(state, is_ket=False) - me.hamiltonians[1].right_multiply(state,
                                                                                                                     is_ket=False))
            if t >= i and t < i+.1:
                for noise_model in me.jump_operators:
                    res = res + noise_model.all_qubit_liouvillian(state)
            return res
        #res = me.run_ode_solver(s, 0, i+l+.1, 100, func = f_var_diss)
        res = me.run_ode_solver(s, 0, i+l, num=500, func = f_MIS)
        costs[n,m] = np.trace(res[-1] @ np.diag(C)@ is_proj)
        n+=1
    m += 1
print(costs)
"""
s.codes = zero
me = master_equation.MasterEquation(hamiltonians = [hb_x, hb_y], jump_operators = [rydberg_noise])
def f_MIS(codes, t):
    # hbar is set to zero
    global i
    res = np.zeros(codes.shape)
    s.codes = codes
    res = res + -1j * (
        hMIS.left_multiply(s, overwrite=False) - hMIS.right_multiply(s, overwrite=False))
    if t>0:
        res = res + -1j * (me.hamiltonians[0].left_multiply(s, overwrite=False) - me.hamiltonians[0].right_multiply(s, overwrite=False))
    else:
        res = res + -1j * (me.hamiltonians[1].left_multiply(s, overwrite=False) - me.hamiltonians[1].right_multiply(s, overwrite=False))
    return res
def f_EIT(codes, t):
    # hbar is set to zero
    global i
    res = np.zeros(codes.shape)
    s.codes = codes
    if t>0:
        res = res + -1j * (me.hamiltonians[0].left_multiply(s, overwrite=False) - me.hamiltonians[0].right_multiply(s, overwrite=False))
    else:
        res = res + -1j * (me.hamiltonians[1].left_multiply(s, overwrite=False) - me.hamiltonians[1].right_multiply(s, overwrite=False))
    for noise_model in me.jump_operators:
        res = res + noise_model.all_qubit_liouvillian(codes)
    return res
res = me.run_ode_solver(s, 0, np.pi/(2*np.sqrt(3))-.05, 1000, func = f_MIS)
print(np.trace(res[-1] @ np.diag(C)@ is_proj))
s.codes = zero
res = me.run_ode_solver(s, 0, np.pi/(2*np.sqrt(3)), 1000, func = f_EIT)
print(np.trace(res[-1] @ np.diag(C)@ is_proj))
"""

plt.imshow(costs, vmin=0, vmax=1, extent = [0, 2*np.pi, 2*np.pi, 0])
plt.title(r'Rydberg EIT QAOA')
plt.ylabel(r'$t_Y$')
plt.xlabel(r'$t_X$')
plt.colorbar()
plt.show()




"""for N in range(2, 7):
    print(N)
    zero = np.zeros([1, 2**N])
    zero[0,0] = 1
    zero = zero.T
    s = State(tools.outer_product(zero, zero), N)
    G = nx.complete_graph(N)
    rydberg_noise = lindblad_operators.RydbergNoise(N, rydberg_noise_rate, G)
    rydberg_noise.weights = 1
    me = master_equation.MasterEquation(hamiltonians=[], lindblad_operators=[rydberg_noise])
    time_res = me.run_ode_solver(s, 0, 1, 20)
    is_proj = IS_projector(G)
    is_proj = [np.trace(time_res[i]@is_proj) for i in range(time_res.shape[0])]
    plt.plot(np.linspace(0, 1, len(is_proj)), is_proj, label = r'$N = $'+str(N))
    plt.title(r'Complete graph evolution of $|{1}\rangle^N$ under Rydberg EIT')
    plt.xlabel(r't')
    plt.ylabel(r'tr$(\rho \Pi_{IS})$')
plt.legend(loc = 'lower right')
plt.show()"""