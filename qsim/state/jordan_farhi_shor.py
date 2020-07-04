import numpy as np
from qsim import tools
from . import qubit
from scipy.linalg import expm

"""
:class:`JordanFarhiShor` is an error detecting code which detects phase flip (Z-type) and bit flip (X-type) errors.
These errors cannot be corrected unambiguously.
"""
X = tools.tensor_product([tools.Y(), tools.identity(), tools.Y(), tools.identity()])
Y = tools.tensor_product([-1 * tools.identity(), tools.X(), tools.X(), tools.identity()])
Z = tools.tensor_product([tools.Z(), tools.Z(), tools.identity(), tools.identity()])
n = 4
d=2
logical_basis = np.array([[[1], [0], [0], [1j], [0], [0], [0], [0], [0], [0], [0], [0], [1j], [0], [0], [1]],
                  [[0], [0], [0], [0], [0], [-1], [1j], [0], [0], [1j], [-1], [0], [0], [0], [0], [0]]]) / 2
U = tools.tensor_product([logical_basis[0], logical_basis[0]])
stabilizers = np.array(
    [tools.X(4), tools.Z(4), tools.tensor_product([tools.X(), tools.Y(), tools.Z(), tools.identity()])])
codespace_projector = tools.outer_product(logical_basis[0], logical_basis[0]) + tools.outer_product(logical_basis[1], logical_basis[1])



def rotation(state, apply_to, angle: float, op, is_ket=False, pauli=False, is_involutary=False, is_idempotent=False):
    """
    Apply a single qubit rotation :math:`e^{-i \\alpha A}` to the input ``state``.

    :param is_idempotent:
    :param is_involutary:
    :param state: input wavefunction or density matrix
    :type state: np.ndarray
    :param i: zero-based index of qudit location to apply the Pauli operator
    :type i: int
    :param angle: The angle :math:`\\alpha`` to rotate by.
    :type angle: float
    :param op: Operator to act with.
    :type op: np.ndarray
    :param is_ket: Boolean dictating whether the input is a density matrix or a ket
    :type is_ket: bool
    :param d: Integer representing the dimension of the qudit
    :type d: int
    """
    if pauli:
        # Construct operator to use
        temp = []
        for i in range(len(op)):
            if op[i] == 'X':
                temp.append(X)
            elif op[i] == 'Y':
                temp.append(Y)
            elif op[i] == 'Z':
                temp.append(Z)
        temp = tools.tensor_product(temp)
        temp = np.cos(angle) * np.identity(temp.shape[0]) - temp * 1j * np.sin(angle)
        return multiply(state, apply_to, temp, is_ket=is_ket, pauli=False)
    else:
        if is_involutary:
            op = np.cos(angle) * np.identity(op.shape[0]) - op * 1j * np.sin(angle)
            return multiply(state, apply_to, op, is_ket=is_ket, pauli=False)
        elif is_idempotent:
            op = (np.exp(-1j * angle) - 1) * op + np.identity(op.shape[0])
            return multiply(state, apply_to, op, is_ket=is_ket, pauli=False)
        else:
            return multiply(state, apply_to, expm(-1j * angle * op), is_ket=is_ket, pauli=False)


def left_multiply(state, apply_to: list, op, is_ket=False, pauli=False):
    """
    Apply a multi-qubit operator on several qubits (indexed in apply_to) of the input state.
    :param state: input wavefunction or density matrix
    :type state: np.ndarray
    :param apply_to: zero-based indices of qudit locations to apply the operator
    :type apply_to: list of int
    :param op: Operator to act with.
    :type op: np.ndarray (2-dimensional)
    :param is_ket: Boolean dictating whether the input is a density matrix or a ket
    :type is_ket: bool
    """
    n_op = len(apply_to)
    N = state.shape[0]
    if not pauli:
        if tools.is_sorted(apply_to):
            # Generate all shapes for left multiplication
            preshape = (d**n) * np.ones((2, n_op), dtype=int)
            preshape[1, 0] = int(N / ((d**n) ** (1 + apply_to[n_op - 1])))
            if n_op > 1:
                preshape[1, 1:] = np.flip((d**n) ** np.diff(apply_to)) / (d**n)

            shape1 = np.zeros(2 * n_op + 1, dtype=int)
            shape2 = np.zeros(2 * n_op + 1, dtype=int)
            order1 = np.zeros(2 * n_op + 1, dtype=int)
            order2 = np.zeros(2 * n_op + 1, dtype=int)

            shape1[:-1] = np.flip(preshape, axis=0).reshape((2 * n_op), order='F')
            shape1[-1] = -1
            shape2[:-1] = preshape.reshape((-1), order='C')
            shape2[-1] = -1

            preorder = np.arange(2 * n_op)
            order1[:-1] = np.flip(preorder.reshape((-1, 2), order='C'), axis=1).reshape((-1), order='F')
            order2[:-1] = np.flip(preorder.reshape((2, -1), order='C'), axis=0).reshape((-1), order='F')
            order1[-1] = 2 * n_op
            order2[-1] = 2 * n_op

            # Now left multiply
            out = state.reshape(shape1, order='F').transpose(order1)
            out = np.dot(op, out.reshape(((d**n) ** n_op, -1), order='F'))
            out = out.reshape(shape2, order='F').transpose(order2)
            out = out.reshape(state.shape, order='F')
            return out
        else:
            # Need to reshape the operator given
            new_shape = (d**n) * np.ones(2 * n_op, dtype=int)
            permut = np.argsort(apply_to)
            transpose_ord = np.zeros(2 * n_op, dtype=int)
            transpose_ord[:n_op] = permut
            transpose_ord[n_op:] = n_op * np.ones(n_op, dtype=int) + permut

            sorted_op = np.reshape(np.transpose(np.reshape(op, new_shape, order='F'), axes=transpose_ord),
                                   ((d**n) ** n_op, (d**n) ** n_op), order='F')
            sorted_applyto = apply_to[permut]

            return left_multiply(state, sorted_applyto, sorted_op, is_ket=is_ket, pauli=pauli)
    else:
        # op should be a list of Pauli operators, or
        out = state.copy()
        # Type handler
        if isinstance(apply_to, int):
            apply_to = [apply_to]
        for i in range(len(apply_to)):
            if op[i] == 'X':  # Sigma_X
                out = qubit.left_multiply(out, [n * apply_to[i], n * apply_to[i]+2], ['Y', 'Y'],
                                          is_ket=is_ket, pauli=True)
            elif op[i] == 'Y':  # Sigma_Y
                out = -1 * qubit.left_multiply(out, [n * apply_to[i]+1, n * apply_to[i]+2], ['X', 'X'],
                                          is_ket=is_ket, pauli=True)
            elif op[i] == 'Z':  # Sigma_Z
                out = qubit.left_multiply(out, [n * apply_to[i], n * apply_to[i]+1], ['Z', 'Z'],
                                          is_ket=is_ket, pauli=True)
        return out


def right_multiply(state, apply_to: list, op, is_ket=False, pauli=False):
    """
    Apply a multi-qubit operator on several qubits (indexed in apply_to) of the input state.
    :param pauli:
    :param state: input wavefunction or density matrix
    :type state: np.ndarray
    :param apply_to: zero-based indices of qudit locations to apply the operator
    :type apply_to: list of int
    :param op: Operator to act with.
    :type op: np.ndarray (2-dimensional)
    :param is_ket: Boolean dictating whether the input is a density matrix or a ket
    :type is_ket: bool
    """
    assert not is_ket, 'Right multiply functionality currently only exists for density matrices.'
    n_op = len(apply_to)
    N = state.shape[0]
    if not pauli:
        if tools.is_sorted(apply_to):
            # generate necessary shapes
            preshape = (d**n) * np.ones((2, n_op), dtype=int)
            preshape[0, 0] = int(N / ((d**n) ** (1 + apply_to[n_op - 1])))
            if n_op > 1:
                preshape[0, 1:] = np.flip((d**n) ** np.diff(apply_to)) / (d**n)

            shape3 = np.zeros(2 * n_op + 2, dtype=int)
            shape3[0] = N
            shape3[1:-1] = np.reshape(preshape, (2 * n_op), order='F')
            shape3[-1] = -1

            shape4 = np.zeros(2 * n_op + 2, dtype=int)
            shape4[0] = N
            shape4[1:n_op + 1] = preshape[0]
            shape4[n_op + 1] = -1
            shape4[n_op + 2:] = preshape[1]

            order3 = np.zeros(2 * n_op + 2, dtype=int)
            order3[0] = 0
            order3[1:n_op + 2] = 2 * np.arange(n_op + 1) + np.ones(n_op + 1)
            order3[n_op + 2:] = 2 * np.arange(1, n_op + 1)

            order4 = np.zeros(2 * n_op + 2, dtype=int)
            order4[0] = 0
            order4[1] = 1
            order4[2:] = np.flip(np.arange(2, 2 * n_op + 2).reshape((2, -1), order='C'), axis=0).reshape((-1), order='F')

            # right multiply
            out = state.reshape(shape3, order='F').transpose(order3)
            out = np.dot(out.reshape((-1, (d**n) ** n_op), order='F'), op.conj().T)
            out = out.reshape(shape4, order='F').transpose(order4)
            out = out.reshape(state.shape, order='F')
            return out
        else:
            new_shape = 2 * np.ones(2 * n_op, dtype=int)
            permut = np.argsort(apply_to)
            transpose_ord = np.zeros(2 * n_op, dtype=int)
            transpose_ord[:n_op] = permut
            transpose_ord[n_op:] = n_op * np.ones(n_op, dtype=int) + permut

            sorted_op = np.reshape(np.transpose(np.reshape(op, new_shape, order='F'), axes=transpose_ord),
                                   ((d**n) ** n_op, (d**n) ** n_op), order='F')
            sorted_applyto = apply_to[permut]

            return right_multiply(state, sorted_applyto, sorted_op, is_ket=is_ket, pauli=pauli)
    else:
        out = state.copy()
        # Type handler:
        if isinstance(apply_to, int):
            apply_to = [apply_to]
        for i in range(len(apply_to)):
            # Note index start from the right (sN,...,s3,s2,s1)
            if op[i] == 'X':  # Sigma_X
                out = qubit.left_multiply(out, [n * apply_to[i], n * apply_to[i]+2], ['Y', 'Y'],
                                          is_ket=is_ket, pauli=True)
            elif op[i] == 'Y':  # Sigma_Y
                out = -1 * qubit.left_multiply(out, [n * apply_to[i]+1, n * apply_to[i]+2], ['X', 'X'],
                                          is_ket=is_ket, pauli=True)
            elif op[i] == 'Z':  # Sigma_Z
                out = qubit.left_multiply(out, [n * apply_to[i], n * apply_to[i]+1], ['Z', 'Z'],
                                          is_ket=is_ket, pauli=True)
        return out


def multiply(state, apply_to: list, op, is_ket=False, pauli=False):
    """
    Apply a multi-qubit operator on several qubits (indexed in apply_to) of the input state.
    :param state: input wavefunction or density matrix
    :type state: np.ndarray
    :param apply_to: zero-based indices of qudit locations to apply the operator
    :type apply_to: list of int
    :param op: Operator to act with.
    :type op: np.ndarray (2-dimensional)
    :param is_ket: Boolean dictating whether the input is a density matrix or a ket
    :type is_ket: bool
    """
    if not is_ket:
        if pauli:
            out = state.copy()
            # Type handler:
            if isinstance(apply_to, int):
                apply_to = [apply_to]
            for i in range(len(apply_to)):
                # Note index start from the right (sN,...,s3,s2,s1)
                # Note index start from the right (sN,...,s3,s2,s1)
                if op[i] == 'X':  # Sigma_X
                    out = qubit.left_multiply(out, [n * apply_to[i], n * apply_to[i] + 2], ['Y', 'Y'],
                                              is_ket=is_ket, pauli=True)
                elif op[i] == 'Y':  # Sigma_Y
                    out = -1 * qubit.left_multiply(out, [n * apply_to[i] + 1, n * apply_to[i] + 2], ['X', 'X'],
                                                   is_ket=is_ket, pauli=True)
                elif op[i] == 'Z':  # Sigma_Z
                    out = qubit.left_multiply(out, [n * apply_to[i], n * apply_to[i] + 1], ['Z', 'Z'],
                                              is_ket=is_ket, pauli=True)
            return out
        else:
            return right_multiply(left_multiply(state, apply_to, op, is_ket=is_ket, pauli=pauli), apply_to, op,
                                  is_ket=is_ket,
                                  pauli=pauli)
    else:
        return left_multiply(state, apply_to, op, is_ket=is_ket, pauli=pauli)