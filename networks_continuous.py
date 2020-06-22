import torch
import torch.nn as nn
import numpy as np
from networks import SQXNet, TaskHeadActor, TaskHeadCritic


class ContinuousActor(SQXNet):
    """Class for policy (or actor) network"""

    def __init__(self,
                 state_dim=3,
                 base_hidden_size=32,
                 num_intentions=1,
                 head_input_size=16,
                 head_hidden_size=8,
                 head_output_size=4,
                 action_dim=1,
                 non_linear=torch.nn.ELU(),
                 net_type=TaskHeadActor,
                 batch_norm=False,
                 use_gpu=True):
        super(ContinuousActor, self).__init__(state_dim,
                                              base_hidden_size,
                                              num_intentions,
                                              head_input_size,
                                              head_hidden_size,
                                              action_dim * 2,
                                              non_linear,
                                              net_type,
                                              batch_norm,
                                              use_gpu)
        self.logits = nn.Tanh()
        self.action_dim = action_dim

    def predict(self, x, task=None, action=None, log_prob=True):
        x = self(x, task)
        x = self.logits(x)
        assert x.shape[-1] == self.action_dim * 2
        # Intention head determines parameters of Categorical distribution
        means = x[self.action_dim:] * 2
        standard_deviations = x[:self.action_dim]
        dist = torch.distributions.Normal(means, standard_deviations)
        if action is None:
            action = dist.sample()
        log_prob = dist.log_prob(action)
        return action, log_prob


class ContinuousCritic(SQXNet):
    """Class for Q-function (or critic) network"""

    def __init__(self,
                 num_intentions=6,
                 state_dim=9,
                 base_hidden_size=64,
                 head_input_size=64,
                 head_hidden_size=32,
                 head_output_size=1,
                 non_linear=torch.nn.ELU(),
                 net_type=TaskHeadCritic,
                 batch_norm=False,
                 use_gpu=True):
        super(ContinuousCritic, self).__init__(state_dim,
                                               base_hidden_size,
                                               num_intentions,
                                               head_input_size,
                                               head_hidden_size,
                                               head_output_size,
                                               non_linear,
                                               net_type,
                                               batch_norm,
                                               use_gpu)

    def forward(self, x, task=None):
        if x.dim() <= 2:
            return super().forward(x, task).squeeze()
        else:
            assert x.dim() == 3
            assert x.shape[1] == self.num_intentions
            x_list = list()
            for i in range(self.num_intentions):
                x_list.append(super().forward(x[:, i, :].squeeze(), i))
            x = torch.cat(x_list, dim=1)
            return x


if __name__ == '__main__':
    print('Run this file directly to debug')

    actor = ContinuousActor()
    critic = ContinuousCritic()

    # Carry out a step on the environment to test out forward functions
    import gym

    env = gym.make('LunarLander-v2')
    obs = env.reset()
    task_idx = np.random.randint(6)

    # Get the action from current actor policy
    action = actor.predict(torch.tensor([obs]), task_idx)
    _, _, _, _ = env.step(action.item())

    print('Got to end sucessfully! (Though this only means there are no major bugs..)')
