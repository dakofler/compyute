"""Normalization layers module"""

from typing import Optional

from ...base_tensor import Tensor, _ShapeLike
from ...dtypes import Dtype, _DtypeLike
from ...tensor_functions.creating import ones, zeros
from ..functional.normalizatons import batchnorm1d, batchnorm2d, layernorm
from ..parameter import Buffer, Parameter
from .module import Module

__all__ = ["Batchnorm1d", "Batchnorm2d", "Layernorm"]


class Batchnorm1d(Module):
    """Batch Normalization."""

    __slots__ = ("channels", "eps", "m", "dtype", "w", "b", "rmean", "rvar")

    def __init__(
        self,
        channels: int,
        eps: float = 1e-5,
        m: float = 0.1,
        dtype: _DtypeLike = Dtype.FLOAT32,
        label: Optional[str] = None,
        training: bool = False,
    ) -> None:
        """Implements Batch Normalization.
        Input: (B, C, T) or (B, C)
            B ... batch, C ... channels, T ... time
        Output: (B, C, T) or (B, C)
            B ... batch, C ... channels, T ... time
        Normalizes over the C dimension.

        Parameters
        ----------
        channels : int
            Number of channels.
        eps : float, optional
            Constant for numerical stability, by default 1e-5.
        m : float, optional
            Momentum used for running mean and variance computation, by default 0.1.
        dtype: DtypeLike, optional
            Datatype of weights and biases, by default Dtype.FLOAT32.
        label: str, optional
            Module label.
        training: bool, optional
            Whether the module should be in training mode, by default False.
        """
        super().__init__(label, training)
        self.channels = channels
        self.eps = eps
        self.m = m
        self.dtype = Dtype(dtype)

        # parameters
        self.w = Parameter(ones((channels,), dtype), label="bn1d_w")
        self.b = Parameter(zeros((channels,), dtype), label="bn1d_b")

        # buffers
        self.rmean = Buffer(zeros((channels,), dtype), label="bn1d_rmean")
        self.rvar = Buffer(ones((channels,), dtype), label="bn1d_rvar")

    def forward(self, x: Tensor) -> Tensor:
        self._check_dims(x, [2, 3])
        x = x.as_type(self.dtype)

        y, self.rmean, self.rvar, grad_func = batchnorm1d(
            x, self.rmean, self.rvar, self.w, self.b, self.m, self.eps, self._training
        )

        if self._training and grad_func is not None:

            def _backward(dy: Tensor) -> Tensor:
                dy = dy.as_type(self.dtype)
                dx, dw, db = grad_func(dy)

                if dw is not None:
                    self.w.grad += dw

                if db is not None:
                    self.b.grad += db

                return dx

            self._backward = _backward

        return y


class Batchnorm2d(Module):
    """Batch Normalization."""

    __slots__ = ("channels", "eps", "m", "dtype", "w", "b", "rmean", "rvar")

    def __init__(
        self,
        channels: int,
        eps: float = 1e-5,
        m: float = 0.1,
        dtype: _DtypeLike = Dtype.FLOAT32,
        label: Optional[str] = None,
        training: bool = False,
    ) -> None:
        """Implements Batch Normalization.
        Input: (B, C, Y, X)
            B ... batch, C ... channels, Y ... height, X ... width
        Output: (B, C, Y, X)
            B ... batch, C ... channels, Y ... height, X ... width
        Normalizes over the C dimension.

        Parameters
        ----------
        channels : int
            Number of channels.
        eps : float, optional
            Constant for numerical stability, by default 1e-5.
        m : float, optional
            Momentum used for running mean and variance computation, by default 0.1.
        dtype: DtypeLike, optional
            Datatype of weights and biases, by default Dtype.FLOAT32.
        label: str, optional
            Module label.
        training: bool, optional
            Whether the module should be in training mode, by default False.
        """
        super().__init__(label, training)
        self.channels = channels
        self.eps = eps
        self.m = m
        self.dtype = Dtype(dtype)

        # parameters
        self.w = Parameter(ones((channels,), dtype), label="bn2d_w")
        self.b = Parameter(zeros((channels,), dtype), label="bn2d_b")

        # buffers
        self.rmean = Buffer(zeros((channels,), dtype), label="bn2d_rmean")
        self.rvar = Buffer(ones((channels,), dtype), label="bn2d_rvar")

    def forward(self, x: Tensor) -> Tensor:
        self._check_dims(x, [4])
        x = x.as_type(self.dtype)

        y, self.rmean, self.rvar, grad_func = batchnorm2d(
            x, self.rmean, self.rvar, self.w, self.b, self.m, self.eps, self._training
        )

        if self._training and grad_func is not None:

            def _backward(dy: Tensor) -> Tensor:
                dy = dy.as_type(self.dtype)
                dx, dw, db = grad_func(dy)

                if dw is not None:
                    self.w.grad += dw

                if db is not None:
                    self.b.grad += db

                return dx

            self._backward = _backward

        return y


class Layernorm(Module):
    """Normalizes values per sample."""

    __slots__ = ("normalized_shape", "eps", "dtype", "w", "b")

    def __init__(
        self,
        normalized_shape: _ShapeLike,
        eps: float = 1e-5,
        dtype: _DtypeLike = Dtype.FLOAT32,
        label: Optional[str] = None,
        training: bool = False,
    ) -> None:
        """Implements layer normalization.
        Input: (B, ...)
            B ... batch
        Output: (B, ...)
            B ... batch
        Normalizes over all trailing dimensions.

        Parameters
        ----------
        normalized_shape : ShapeLike
            Shape of the normalized tensor ignoring the batch dimension.
        eps : float, optional
            Constant for numerical stability, by default 1e-5.
        dtype: DtypeLike, optional
            Datatype of weights and biases, by default Dtype.FLOAT32.
        label: str, optional
            Module label.
        training: bool, optional
            Whether the module should be in training mode, by default False.
        """
        super().__init__(label, training)
        self.normalized_shape = normalized_shape
        self.eps = eps
        self.dtype = Dtype(dtype)

        # parameters
        self.w = Parameter(ones(normalized_shape, dtype), label="ln_w")
        self.b = Parameter(zeros(normalized_shape, dtype), label="ln_b")

    def forward(self, x: Tensor) -> Tensor:
        x = x.as_type(self.dtype)

        y, grad_func = layernorm(x, self.w, self.b, self.eps, self._training)

        if self._training and grad_func is not None:

            def _backward(dy: Tensor) -> Tensor:
                dy = dy.as_type(self.dtype)
                dx, dw, db = grad_func(dy)

                if dw is not None:
                    self.w.grad += dw

                if db is not None:
                    self.b.grad += db

                return dx

            self._backward = _backward

        return y