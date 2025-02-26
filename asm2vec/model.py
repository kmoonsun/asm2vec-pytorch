import torch
import torch.nn as nn

bce, sigmoid, softmax = nn.BCELoss(), nn.Sigmoid(), nn.Softmax(dim=1)

class ASM2VEC(nn.Module):
    def __init__(self, vocab_size, function_size, embedding_size):
        super(ASM2VEC, self).__init__()
        # Create an embedding layer for the vocabulary, initializing weights with zeros
        self.embeddings = nn.Embedding(vocab_size, embedding_size, _weight=torch.zeros(vocab_size, embedding_size))
        # Create an embedding layer for functions, initializing weights randomly
        self.embeddings_f = nn.Embedding(function_size, 2 * embedding_size, _weight=(torch.rand(function_size, 2 * embedding_size)-0.5)/embedding_size/2)
        # Create an embedding layer for relations, initializing weights randomly
        self.embeddings_r = nn.Embedding(vocab_size, 2 * embedding_size, _weight=(torch.rand(vocab_size, 2 * embedding_size)-0.5)/embedding_size/2)

    def update(self, function_size_new, vocab_size_new):
        # Update the embeddings if the vocabulary or function sizes change
        device = self.embeddings.weight.device
        vocab_size, function_size, embedding_size = self.embeddings.num_embeddings, self.embeddings_f.num_embeddings, self.embeddings.embedding_dim
        if vocab_size_new != vocab_size:
            # Update vocabulary embeddings with new size
            weight = torch.cat([self.embeddings.weight, torch.zeros(vocab_size_new - vocab_size, embedding_size).to(device)])
            self.embeddings = nn.Embedding(vocab_size_new, embedding_size, _weight=weight)
            # Update relation embeddings with new size
            weight_r = torch.cat([self.embeddings_r.weight, ((torch.rand(vocab_size_new - vocab_size, 2 * embedding_size)-0.5)/embedding_size/2).to(device)])
            self.embeddings_r = nn.Embedding(vocab_size_new, 2 * embedding_size, _weight=weight_r)
        # Update function embeddings with new size
        self.embeddings_f = nn.Embedding(function_size_new, 2 * embedding_size, _weight=((torch.rand(function_size_new, 2 * embedding_size)-0.5)/embedding_size/2).to(device))

    def v(self, inp):
        # Calculate the vertex representations
        e  = self.embeddings(inp[:,1:])
        v_f = self.embeddings_f(inp[:,0])
        v_prev = torch.cat([e[:,0], (e[:,1] + e[:,2]) / 2], dim=1)
        v_next = torch.cat([e[:,3], (e[:,4] + e[:,5]) / 2], dim=1)
        v = ((v_f + v_prev + v_next) / 3).unsqueeze(2)
        return v

    def forward(self, inp, pos, neg):
        # Forward pass calculating the loss
        device, batch_size = inp.device, inp.shape[0]
        v = self.v(inp)
        # Compute the negative sampling loss
        pred = torch.bmm(self.embeddings_r(torch.cat([pos, neg], dim=1)), v).squeeze()
        label = torch.cat([torch.ones(batch_size, 3), torch.zeros(batch_size, neg.shape[1])], dim=1).to(device)
        return bce(sigmoid(pred), label)

    def predict(self, inp, pos):
        # Make predictions using the vertex representations
        device, batch_size = inp.device, inp.shape[0]
        v = self.v(inp)
        probs = torch.bmm(self.embeddings_r(torch.arange(self.embeddings_r.num_embeddings).repeat(batch_size, 1).to(device)), v).squeeze(dim=2)
        return softmax(probs)
