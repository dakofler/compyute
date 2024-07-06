"""Tensor reshaping layers module"""

from typing import Optional

from ...base_tensor import Tensor, _ShapeLike
from ...tensor_functions.reshaping import moveaxis, reshape
from .module import Module

__all__ = ["Reshape", "Flatten", "Moveaxis"]


class Reshape(Module):
    """Flatten layer used to reshape tensors to any shape."""

    __slots__ = ("output_shape",)

    def __init__(
        self, output_shape: _ShapeLike, label: Optional[str] = None, training: bool = False
    ) -> None:
        """Reshapes a tensor to fit a given shape.

        Parameters
        ----------
        output_shape : ShapeLike
            The output's target shape not including the batch dimension.
        label: str, optional
            Module label.
        training: bool, optional
            Whether the module should be in training mode, by default False.
        """
        super().__init__(label, training)
        self.output_shape = output_shape

    def forward(self, x: Tensor) -> Tensor:
        y = reshape(x, shape=(x.shape[0],) + self.output_shape)

        if self.training:
            self._backward = lambda dy: reshape(dy, shape=x.shape)

        return y


class Flatten(Module):
    """Flatten layer used to flatten tensors not including the batch dimension."""

    __slots__ = ()

    def forward(self, x: Tensor) -> Tensor:
        y = reshape(x, shape=(x.shape[0], -1))

        if self.training:
            self._backward = lambda dy: reshape(dy, shape=x.shape)

        return y


class Moveaxis(Module):
    """Moveaxis layer used to swap tensor dimensions."""

    __slots__ = ("from_axis", "to_axis")

    def __init__(
        self, from_axis: int, to_axis: int, label: Optional[str] = None, training: bool = False
    ) -> None:
        """Reshapes a tensor to fit a given shape.

        Parameters
        ----------
        from_axis : int
            Original positions of the axes to move. These must be unique.
        to_axis : int
            Destination positions for each of the original axes. These must also be unique.
        label: str, optional
            Module label.
        training: bool, optional
            Whether the module should be in training mode, by default False.
        """
        super().__init__(label, training)
        self.from_axis = from_axis
        self.to_axis = to_axis

    def forward(self, x: Tensor) -> Tensor:
        y = moveaxis(x, from_axis=self.from_axis, to_axis=self.to_axis)

        if self.training:
            self._backward = lambda dy: moveaxis(dy, from_axis=self.from_axis, to_axis=self.to_axis)

        return y
