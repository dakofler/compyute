"""Neural network convolution modules."""

import math
from typing import Literal, Optional

from ...base_tensor import Tensor
from ...random.random import uniform
from ...tensor_ops.creating import zeros
from ...typing import DType, float32
from ..functional.convolutions import (
    _PaddingLike,
    avgpooling2d,
    convolve1d,
    convolve2d,
    maxpooling2d,
)
from ..parameter import Parameter, update_parameter_grad
from .module import Module, validate_input_axes

__all__ = ["Convolution1D", "Convolution2D", "MaxPooling2D", "AvgPooling2D"]


class Convolution1D(Module):
    r"""Applies a 1D convolution to the input for feature extraction.

    .. math::
        y = b + \sum_{k=0}^{C_{in}-1} w_{k}*x_{k}

    where :math:`*` is the cross-correlation operator.

    Shapes:
        - Input :math:`(B, C_{in}, S_{in})`
        - Output :math:`(B, C_{out}, S_{out})`
    where
        - :math:`B` ... batch axis
        - :math:`C_{in}` ... input channels
        - :math:`S_{in}` ... input sequence
        - :math:`C_{out}` ... output channels
        - :math:`S_{out}` ... output sequence

    Parameters
    ----------
    in_channels : int
        Number of input channels.
    out_channels : int
        Number of output channels (filters).
    kernel_size : int
        Size of each kernel.
    padding : _PaddingLike, optional
        Padding applied before convolution. Defaults to ``valid``.
    stride : int, optional
        Stride used for the convolution operation. Defaults to ``1``.
    dilation : int, optional
        Dilation used for each axis of the filter. Defaults to ``1``.
    bias : bool, optional
        Whether to use bias values. Defaults to ``True``.
    dtype : DType, optional
        Datatype of weights and biases. Defaults to :class:`compyute.float32`.
    label : str, optional
        Module label. Defaults to ``None``. If ``None``, the class name is used.


    .. note::
        Weights are initialized from :math:`\mathcal{U}(-k, k)`, where
        :math:`k = \sqrt{\frac{1}{C_{in} \cdot \text{kernel_size}}}`. Biases are initialized as zeros.
    """

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: int,
        padding: Literal["valid", "same"] = "valid",
        stride: int = 1,
        dilation: int = 1,
        bias: bool = True,
        dtype: DType = float32,
        label: Optional[str] = None,
    ) -> None:
        super().__init__(label)
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.kernel_size = kernel_size
        self.padding = padding
        self.stride = stride
        self.dilation = dilation
        self.bias = bias

        # init weights
        k = 1 / math.sqrt(in_channels * kernel_size)
        self.w = Parameter(
            uniform((out_channels, in_channels, kernel_size), -k, k, dtype)
        )

        # init biases
        self.b = Parameter(zeros((out_channels,), dtype)) if bias else None

    def forward(self, x: Tensor) -> Tensor:
        validate_input_axes(self, x, [3])

        y, grad_fn = convolve1d(
            x,
            self.w,
            self.b,
            self.padding,
            self.stride,
            self.dilation,
            self._is_training,
        )

        if self._is_training and grad_fn is not None:

            def _backward(dy: Tensor) -> Tensor:
                dx, dw, db = grad_fn(dy)
                update_parameter_grad(self.w, dw)
                update_parameter_grad(self.b, db)
                return dx

            self._backward = _backward

        return y


class Convolution2D(Module):
    r"""Applies a 2D convolution to the input for feature extraction.

    .. math::
        y = b + \sum_{k=0}^{C_{in}-1} w_{k}*x_{k}

    where :math:`*` is the cross-correlation operator.

    Shapes:
        - Input :math:`(B, C_{in}, Y_{in}, X_{in})`
        - Output :math:`(B, C_{out}, Y_{out}, X_{out})`
    where
        - :math:`B` ... batch axis
        - :math:`C_{in}` ... input channels
        - :math:`Y_{in}` ... input height
        - :math:`X_{in}` ... input width
        - :math:`C_{out}` ... output channels
        - :math:`Y_{out}` ... output height
        - :math:`X_{out}` ... output width

    Parameters
    ----------
    in_channels : int
        Number of input channels (color channels).
    out_channels : int
        Number of output channels (filters or feature maps).
    kernel_size : int
        Size of each kernel.
    padding : _PaddingLike, optional
        Padding applied before convolution. Defaults to ``valid``.
    stride : int , optional
        Strides used for the convolution operation. Defaults to ``1``.
    dilation : int , optional
        Dilations used for each axis of the filter. Defaults to ``1``.
    bias : bool, optional
        Whether to use bias values. Defaults to ``True``.


    .. note::
        Weights are initialized from :math:`\mathcal{U}(-k, k)`, where
        :math:`k = \sqrt{\frac{1}{C_{in} * \text{kernel_size}^2}}`. Biases are initialized as zeros.
    """

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: int,
        padding: _PaddingLike = "valid",
        stride: int = 1,
        dilation: int = 1,
        bias: bool = True,
        dtype: DType = float32,
        label: Optional[str] = None,
    ) -> None:
        super().__init__(label)
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.kernel_size = kernel_size
        self.padding = padding
        self.stride = stride
        self.dilation = dilation
        self.bias = bias

        # init weights
        k = 1 / math.sqrt(in_channels * kernel_size**2)
        self.w = Parameter(
            uniform((out_channels, in_channels, kernel_size, kernel_size), -k, k, dtype)
        )

        # init biases
        self.b = Parameter(zeros((out_channels,), dtype)) if bias else None

    def forward(self, x: Tensor) -> Tensor:
        validate_input_axes(self, x, [4])

        y, grad_fn = convolve2d(
            x,
            self.w,
            self.b,
            self.padding,
            self.stride,
            self.dilation,
            self._is_training,
        )

        if self._is_training and grad_fn is not None:

            def _backward(dy: Tensor) -> Tensor:
                dx, dw, db = grad_fn(dy)
                update_parameter_grad(self.w, dw)
                update_parameter_grad(self.b, db)
                return dx

            self._backward = _backward

        return y


class MaxPooling2D(Module):
    """Pooling layer used for downsampling where the
    maximum value within the pooling window is used.

    Parameters
    ----------
    kernel_size : int, optional
        Size of the pooling window used for the pooling operation. Defaults to ``2``.
    """

    def __init__(self, kernel_size: int = 2, label: Optional[str] = None) -> None:
        super().__init__(label)
        self.kernel_size = kernel_size

    def forward(self, x: Tensor) -> Tensor:
        validate_input_axes(self, x, [4])

        kernel_size = (self.kernel_size, self.kernel_size)
        y, self._backward = maxpooling2d(x, kernel_size, self._is_training)
        return y


class AvgPooling2D(Module):
    """Pooling layer used for downsampling where the
    average value within the pooling window is used.

    Parameters
    ----------
    kernel_size : int, optional
        Size of the pooling window used for the pooling operation. Defaults to ``2``.
    """

    def __init__(self, kernel_size: int = 2, label: Optional[str] = None) -> None:
        super().__init__(label)
        self.kernel_size = kernel_size

    def forward(self, x: Tensor) -> Tensor:
        validate_input_axes(self, x, [4])

        kernel_size = (self.kernel_size, self.kernel_size)
        y, self._backward = avgpooling2d(x, kernel_size, self._is_training)
        return y
