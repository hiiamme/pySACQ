import torch
import torch.nn as nn


class RetraceLossRecursive(nn.Module):
    """
    Retrace Loss as defined in
    Munos, Rémi, Stepleton, Tom, Harutyunyan, Anna, and Bellemare, Marc G.
    Safe and efficient off-policy reinforcement learning.
    In Neural Information Processing Systems (NIPS), 2016.
    """

    def __init__(self,
                 gamma=0.99, use_gpu=False):
        super().__init__()
        self.gamma = gamma
        self.distance = nn.SmoothL1Loss()
        self.use_gpu = use_gpu

    def forward(self,
                state_trajectory_action_values,
                target_state_trajectory_action_values,
                target_expected_state_values,
                rewards,
                original_log_trajectory_action_probs,
                target_log_trajectory_task_action_probs):

        state_trajectory_action_values = self.remove_last_timestep(state_trajectory_action_values)
        with torch.no_grad():
            rewards = self.remove_last_timestep(rewards)
            target_state_trajectory_action_values = self.remove_first_timestep(target_state_trajectory_action_values)
            target_expected_state_values = self.remove_first_timestep(target_expected_state_values)
            num_steps = state_trajectory_action_values.shape[0]
            log_importance_weights = (target_log_trajectory_task_action_probs
                                      - original_log_trajectory_action_probs.unsqueeze(-1))
            importance_weights = self.remove_first_timestep(torch.exp(torch.clamp(log_importance_weights, max=0)))
            retrace_state_action_values = torch.zeros_like(state_trajectory_action_values)

            retrace_state_action_values[:, -1, :] = (
                    rewards[:, -1, :]
                    + self.gamma * (target_expected_state_values[:, -1, :]
                                    + importance_weights[:, -1, :] * target_state_trajectory_action_values[:, -1, :]))
            for j in range(num_steps - 2, -1, -1):
                retrace_state_action_values[:, j, :] = (
                        rewards[:, j, :]
                        + self.gamma * (
                                target_expected_state_values[:, j, :]
                                + importance_weights[:, j, :] * (retrace_state_action_values[:, j + 1, :]
                                                                 - target_state_trajectory_action_values[:, j, :])
                        )
                )

        loss = self.distance(state_trajectory_action_values, retrace_state_action_values)
        return loss

    @staticmethod
    def remove_last_timestep(x):
        return x.narrow(-2, 0, x.shape[-2] - 1)

    @staticmethod
    def remove_first_timestep(x):
        return x.narrow(-2, 1, x.shape[-2] - 1)





