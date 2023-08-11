"""parameter layers layer"""

from __future__ import annotations
import numpy as np

from walnut import tensor_utils as tu
from walnut.tensor import Tensor, NumpyArray
from walnut.nn.funcional import convolve1d, convolve2d
from walnut.nn.module import Module


__all__ = ["Linear", "Convolution1d", "Convolution2d", "Embedding"]


class Linear(Module):
    """Fully connected layer."""

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        weights: Tensor | None = None,
        use_bias: bool = True,
    ) -> None:
        """Fully connected layer.

        Parameters
        ----------
        in_channels : int
            Number of input channels of the layer.
        out_channels : int
            Number of output channels (neurons) of the layer.
        weights : Tensor | None, optional
            Weights of the layer, by default None. If None, weights are initialized randomly.
        use_bias : bool, optional
            Whether to use bias values, by default True.
        """
        super().__init__()
        self.use_bias = use_bias

        # init weights (c_in, c_out)
        if weights is None:
            k = in_channels**-0.5
            self.w = tu.randu((in_channels, out_channels), -k, k)
        else:
            self.w = weights
        self.parameters.append(self.w)

        # init bias (c_out,)
        if use_bias:
            self.b = tu.zeros((out_channels,))
            self.parameters.append(self.b)

    def __call__(self, x: Tensor) -> Tensor:
        y = x @ self.w  # (b, [c], c_out)
        if self.use_bias:
            y += self.b

        if self.training:

            def backward(y_grad: NumpyArray) -> NumpyArray:
                dim = x.ndim
                # input grads (b, c_in)
                x_grad = y_grad @ self.w.T

                # weight grads (c_in, c_out)
                w_ax = tuple(d if d < dim - 2 else 2 * dim - d - 3 for d in range(dim))
                self.w.grad = x.transpose(w_ax).data @ y_grad
                if dim > 2:
                    wsum_axis = tuple(np.arange(dim)[:-2])
                    self.w.grad = np.sum(self.w.grad, axis=wsum_axis)

                # bias grads (c_out,)
                if self.use_bias:
                    b_tpl = tuple(d for d in range(dim - 1))
                    self.b.grad = np.sum(y_grad, axis=b_tpl)

                self.set_y_grad(y_grad)
                return x_grad

            self.backward = backward

        self.set_y(y)
        return y


class Convolution1d(Module):
    """Layer used for spacial information and feature extraction."""

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: int,
        pad: str = "valid",
        stride: int = 1,
        dil: int = 1,
        weights: Tensor | None = None,
        use_bias: bool = True,
    ) -> None:
        """Convolutional layer used for spacial information and feature extraction.

        Parameters
        ----------
        in_channels : int
            Number of input channels of the layer.
        out_channels : int
            Number of output channels of the layer.
        kernel_size : int
            Shape of each kernel.
        pad: str, optional
            Padding applied before convolution.
            Options are "valid" and "same", by default "valid".
        stride : int, optional
            Stride used for the convolution operation, by default 1.
        dil : int, optional
            Dilation used for each axis of the filter, by default 1.
        weights : Tensor | None, optional
            Weights of the layer, by default None. If None, weights are initialized randomly.
        use_bias : bool, optional
            Whether to use bias values, by default True.
        """
        super().__init__()
        self.pad = pad
        self.stride = stride
        self.dil = dil
        self.use_bias = use_bias

        # init weights (c_out, c_in, x)
        if weights is None:
            k = int(in_channels * np.prod(kernel_size)) ** -0.5
            self.w = tu.randu((out_channels, in_channels, kernel_size), -k, k)
        else:
            self.w = weights
        self.parameters.append(self.w)

        # init bias (c_out,)
        if use_bias:
            self.b = tu.zeros((out_channels,))
            self.parameters.append(self.b)

    def __call__(self, x: Tensor) -> Tensor:
        # rotate weights for cross correlation
        w_rot = self.w.flip(-1)

        # convolve (b, 1, c_in, x) * (1, c_out, c_in, x)
        x_ext = tu.expand_dims(x, 1)
        w_rot_ext = tu.expand_dims(w_rot, 0)
        x_conv_w = convolve1d(x_ext, w_rot_ext, self.stride, self.dil, self.pad)

        # sum over input channels
        y = x_conv_w.sum(axis=2)

        if self.use_bias:
            y += tu.match_dims(x=self.b, dims=y.ndim - 1)

        if self.training:

            def backward(y_grad: NumpyArray) -> NumpyArray:
                x3 = x.shape[-1]
                w3 = self.w.shape[-1]
                dy1, dy2, dy3 = y_grad.shape

                # undo strides by filling with zeros
                y_grad_p = np.zeros((dy1, dy2, self.stride * dy3))
                y_grad_p[:, :, :: self.stride] = y_grad
                out = 1 + (x3 - w3) if self.pad == "valid" else x3
                y_grad_p = Tensor(y_grad_p[:, :, :out])

                # input grads (b, c_in, x)
                y_grad_p_ext = tu.expand_dims(y_grad_p, 2)
                w_ext = tu.expand_dims(self.w, 0)
                # convolve (b, c_out, 1, x) * (1, c_out, c_in, x)
                pad = "full" if self.pad == "valid" else "same"
                dy_conv_w = convolve1d(y_grad_p_ext, w_ext, dil=self.dil, pad=pad)
                # sum over output channels
                x_grad = dy_conv_w.sum(axis=1).data

                # weight grads (c_out, c_in, x)
                x_ext = tu.expand_dims(x, 1)
                y_grad_p_ext = y_grad_p_ext.flip(-1)
                # convolve (b, 1, c_in, x) * (b, c_out, 1, x)
                pad = w3 // 2 * self.dil if self.pad == "same" else "valid"
                x_conv_dy = convolve1d(x_ext, y_grad_p_ext, pad=pad)[
                    :, :, :, -w3 * self.dil :
                ]
                # sum over batches
                self.w.grad = x_conv_dy[:, :, :, :: self.dil].sum(axis=0).data

                # bias grads (c_out,)
                if self.use_bias:
                    self.b.grad = np.sum(y_grad, axis=(0, 2))  # sum over b and x

                self.set_y_grad(y_grad)
                return x_grad

            self.backward = backward

        self.set_y(y)
        return y


class Convolution2d(Module):
    """Layer used for spacial information and feature extraction."""

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: tuple[int, int] = (3, 3),
        pad: str = "valid",
        stride: int | tuple[int, int] = 1,
        dil: int | tuple[int, int] = 1,
        weights: Tensor | None = None,
        use_bias: bool = True,
    ) -> None:
        """Convolutional layer used for spacial information and feature extraction.

        Parameters
        ----------
        in_channels : int
            Number of input channels of the layer.
        out_channels : int
            Number of output channels (neurons) of the layer.
        kernel_size : ShapeLike, optional
            Shape of each kernel, by default (3, 3).
        pad: str, optional
            Padding applied before convolution.
            Options are "valid" and "same", by default "valid".
        stride : int | tuple [int, int], optional
            Strides used for the convolution operation, by default 1.
        dil : int | tuple [int, int], optional
            Dilations used for each axis of the filter, by default 1.
        weights : Tensor | None, optional
            Weights of the layer, by default None. If None, weights are initialized randomly.
        use_bias : bool, optional
            Whether to use bias values, by default True.
        """
        super().__init__()
        self.pad = pad
        self.stride = (stride, stride) if isinstance(stride, int) else stride
        self.dil = (dil, dil) if isinstance(dil, int) else dil
        self.use_bias = use_bias

        # init weights (c_out, c_in, y, x)
        if weights is None:
            k = int(in_channels * np.prod(kernel_size)) ** -0.5
            self.w = tu.randu((out_channels, in_channels, *kernel_size), -k, k)
        else:
            self.w = weights
        self.parameters.append(self.w)

        # init bias (c_out,)
        if self.use_bias:
            self.b = tu.zeros((out_channels,))
            self.parameters.append(self.b)

    def __call__(self, x: Tensor) -> Tensor:
        # rotate weights for cross correlation
        w_rot = self.w.flip((-2, -1))

        # convolve (b, 1, c_in, y, x) * (1, c_out, c_in, y, x)
        x_ext = tu.expand_dims(x, 1)  # add fake c_out dim
        w_rot_ext = tu.expand_dims(w_rot, 0)  # add fake b dim
        x_conv_w = convolve2d(x_ext, w_rot_ext, self.stride, self.dil, self.pad)

        # sum over input channels
        y = x_conv_w.sum(axis=2)

        if self.use_bias:
            y += tu.match_dims(x=self.b, dims=y.ndim - 1)

        if self.training:

            def backward(y_grad: NumpyArray) -> NumpyArray:
                w3, w4 = self.w.shape[-2:]
                x3, x4 = x.shape[-2:]
                dy1, dy2, dy3, dy4 = y_grad.shape
                s1, s2 = self.stride
                d1, d2 = self.dil

                # fill elements skipped by strides with zeros
                y_grad_p = np.zeros((dy1, dy2, s1 * dy3, s2 * dy4))
                y_grad_p[:, :, ::s1, ::s2] = y_grad
                out_y = 1 + (x3 - w3) if self.pad == "valid" else x3
                out_x = 1 + (x4 - w4) if self.pad == "valid" else x4
                y_grad_p = Tensor(y_grad_p[:, :, :out_y, :out_x])

                # input grads (b, c_in, y, x)
                y_grad_p_ext = tu.expand_dims(y_grad_p, 2)
                w_ext = tu.expand_dims(self.w, 0)
                # convolve (b, c_out, 1, y, x) * (1, c_out, c_in, y, x)
                pad = "full" if self.pad == "valid" else "same"
                dy_conv_w = convolve2d(y_grad_p_ext, w_ext, dil=self.dil, pad=pad)
                x_grad = dy_conv_w.sum(axis=1).data  # sum over output channels

                # weight grads (c_out, c_in, y, x)
                x_ext = tu.expand_dims(x, 1)
                y_grad_p_ext = y_grad_p_ext.flip((-2, -1))
                # convolve (b, 1, c_in, y, x) * (b, c_out, 1, y, x)
                pad = (w3 // 2 * d1, w4 // 2 * d2) if self.pad == "same" else "valid"
                x_conv_dy = convolve2d(x_ext, y_grad_p_ext, pad=pad)[
                    :, :, :, -w3 * d1 :, -w4 * d2 :
                ]
                # sum over batches
                self.w.grad = x_conv_dy[:, :, :, ::d1, ::d2].sum(axis=0).data

                # bias grads (c_out,)
                if self.use_bias:
                    self.b.grad = np.sum(y_grad, axis=(0, 2, 3))  # sum over b, y and x

                self.set_y_grad(y_grad)
                return x_grad

            self.backward = backward

        self.set_y(y)
        return y


class Embedding(Module):
    """Layer used for token embedding."""

    def __init__(
        self, in_channels: int, out_channels: int, weights: Tensor | None = None
    ) -> None:
        """Embedding layer used for token embedding.

        Parameters
        ----------
        in_channels : int
            Number of input channels (vocabulary size) of the layer.
        out_channels : int
            Number of output channels (embedding dimensions) of the layer.
        weights : Tensor | None, optional
            Weights of the layer, by default None. If None, weights are initialized randomly.
        """
        super().__init__()
        # init weights (c_in, c_out)
        if weights is None:
            k = in_channels**-0.5
            self.w = tu.randu((in_channels, out_channels), -k, k)
        else:
            self.w = weights
        self.parameters.append(self.w)

    def __call__(self, x: Tensor) -> Tensor:
        y = x @ self.w

        if self.training:

            def backward(y_grad: NumpyArray) -> NumpyArray:
                x_grad = y_grad @ self.w.T
                self.w.grad = np.sum(x.transpose((0, 2, 1)).data @ y_grad, axis=0)

                self.set_y_grad(y_grad)
                return x_grad

            self.backward = backward

        self.set_y(y)
        return y