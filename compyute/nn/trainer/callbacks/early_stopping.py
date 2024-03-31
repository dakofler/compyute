"""Early stopping callback module"""

from .callback import Callback
from ....tensor import Tensor


__all__ = ["EarlyStopping"]


class EarlyStopping(Callback):
    """Early stopping."""

    def __init__(
        self,
        patience: int = 3,
        use_best_params: bool = True,
        target: str = "loss",
    ) -> None:
        """Aborts the training process if the model stops improving.

        Parameters
        ----------
        patience : int, optional
            Number of epocs without improvement, before the training is aborted, by default 3.
        use_best_params : bool, optional
            Whether to reset the model parameters to the best values found, by default True.
        target : str, optional
            Metric to consider, by default "loss".
        """
        self.patience = patience
        self.use_best_params = use_best_params
        self.target = target
        self.state: dict[str, float | list[Tensor]] = {"best_loss": float("inf")}

    def on_epoch(self, trainer) -> None:
        if self.target not in trainer.state.keys():
            raise ValueError(f"{self.target} not found in trainer state.")

        hist = trainer.state[f"epoch_{self.target}"]
        best_loss = self.state["best_loss"]

        # record best loss
        if hist[-1] < best_loss:
            self.state["best_loss"] = hist[-1]

            # save best parameters
            if self.use_best_params:
                self.state["best_params"] = [p.copy() for p in trainer.model.parameters]

        if len(hist) <= self.patience:
            return

        # check if loss has decreased
        if all([hist[-i] > best_loss for i in range(1, self.patience + 1)]):
            msg = f"Early stopping: no improvement over last {self.patience} epochs."

            # reset model parameters to best epoch
            if self.use_best_params:
                msg += " Resetting parameters best epoch."
                for i, p in enumerate(trainer.model.parameters):
                    p.data = self.state["best_params"][i].data

            print(msg)
            trainer.abort = True