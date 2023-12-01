# -*- coding: utf-8 -*-

import os
import pickle
import random
import numpy as np
import torch
from transformers import BertTokenizer, BertModel


def load_word_vec(path, word2idx=None, embed_dim=768):
    fin = open(path, 'r', encoding='utf-8', newline='\n', errors='ignore')
    word_vec = {}
    for line in fin:
        tokens = line.rstrip().split()
        word, vec = ' '.join(tokens[:-embed_dim]), tokens[-embed_dim:]
        if word in word2idx.keys():
            word_vec[word] = np.asarray(vec, dtype='float32')
    return word_vec


def build_embedding_matrix(word2idx, embed_dim, type):
    embedding_matrix_file_name = '{0}_{1}_embedding_matrix.pkl'.format(str(embed_dim), type)
    if os.path.exists(embedding_matrix_file_name):
        print('loading embedding_matrix:', embedding_matrix_file_name)
        embedding_matrix = pickle.load(open(embedding_matrix_file_name, 'rb'))
    else:
        print('loading word vectors ...')
        embedding_matrix = np.zeros((len(word2idx), embed_dim))  # idx 0 and 1 are all-zeros
        embedding_matrix[1, :] = np.random.uniform(-1/np.sqrt(embed_dim), 1/np.sqrt(embed_dim), (1, embed_dim))
        fname = './glove/glove.840B.300d.txt'
        word_vec = load_word_vec(fname, word2idx=word2idx, embed_dim=embed_dim)
        print('building embedding_matrix:', embedding_matrix_file_name)
        for word, i in word2idx.items():
            vec = word_vec.get(word)
            if vec is not None:
                # words not found in embedding index will be all-zeros.
                embedding_matrix[i] = vec
        pickle.dump(embedding_matrix, open(embedding_matrix_file_name, 'wb'))
    return embedding_matrix

import torch
from transformers import BertTokenizer, BertModel

def build_embedding_matrix_bert(data_raw, embed_dim, type):
    embedding_matrix_file_name = '{0}_{1}_embedding_matrix.pkl'.format(str(embed_dim), type)
    if os.path.exists(embedding_matrix_file_name):
        print('loading embedding_matrix:', embedding_matrix_file_name)
        embedding_matrix = pickle.load(open(embedding_matrix_file_name, 'rb'))
    else:
        print('loading word vectors ...')
        # embedding_matrix = np.zeros((len(data_raw), embed_dim))  # idx 0 and 1 are all-zeros
        # embedding_matrix[1, :] = np.random.uniform(-1/np.sqrt(embed_dim), 1/np.sqrt(embed_dim), (1, embed_dim))
        
        tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
        model = BertModel.from_pretrained("bert-base-uncased")
        
        all_sentence_token_embedding = []            

        for each in data_raw:
            text = " ".join([str(x) for x in each['full_text']])

            inputs = tokenizer.encode_plus(text, return_tensors="pt")
            outputs = model(**inputs)

            last_hidden_states = outputs[0]

            pickle.dump(last_hidden_states, open(embedding_matrix_file_name, 'wb'))
    embedding_matrix = pickle.load(open(embedding_matrix_file_name, 'rb'))
    return embedding_matrix



class Tokenizer(object):
    def __init__(self, word2idx=None):
        if word2idx is None:
            self.word2idx = {}
            self.idx2word = {}
            self.idx = 0
            self.word2idx['<pad>'] = self.idx
            self.idx2word[self.idx] = '<pad>'
            self.idx += 1
            self.word2idx['<unk>'] = self.idx
            self.idx2word[self.idx] = '<unk>'
            self.idx += 1
        else:
            self.word2idx = word2idx
            self.idx2word = {v:k for k,v in word2idx.items()}

    def fit_on_text(self, text):
        text = text.lower()
        words = text.split()
        for word in words:
            if word not in self.word2idx:
                self.word2idx[word] = self.idx
                self.idx2word[self.idx] = word
                self.idx += 1

    def text_to_sequence(self, text):
        text = text.lower()
        words = text.split()
        unknownidx = 1
        sequence = [self.word2idx[w] if w in self.word2idx else unknownidx for w in words]
        # print(len(sequence))
        if len(sequence) == 0:
            sequence = [0]
        return sequence


class ABSADataset(object):
    def __init__(self, data):
        self.data = data

    def __getitem__(self, index):
        return self.data[index]

    def __len__(self):
        return len(self.data)


class ABSADatesetReader:
    @staticmethod
    def __read_text__(fnames):
        text = ''
        for fname in fnames:
            fin = open(fname, 'r', encoding='utf-8', newline='\n', errors='ignore')
            lines = fin.readlines()
            fin.close()
            for i in range(0, len(lines), 3):
                text_left, _, text_right = [s.lower().strip() for s in lines[i].partition("$T$")]
                aspect = lines[i + 1].lower().strip()
                text_raw = text_left + " " + aspect + " " + text_right
                text += text_raw + " "
        return text

    @staticmethod
    def __read_data__(fname, tokenizer):
        fin = open(fname, 'r', encoding='utf-8', newline='\n', errors='ignore')
        lines = fin.readlines()
        fin.close()
        fin = open(fname+'.dist', 'r', encoding='utf-8', newline='\n', errors='ignore')
        dist_lines = fin.readlines()
        fin.close()

        all_data = []
        cnt = 0
        for i in range(0, len(lines), 3):
            text_left, _, text_right = [s.lower().strip() for s in lines[i].partition("$T$")]
            aspect = lines[i + 1].lower().strip()
            polarity = lines[i + 2].strip()

            text_indices = tokenizer.text_to_sequence(text_left + " " + aspect + " " + text_right)
            aspect_indices = tokenizer.text_to_sequence(aspect)
            left_indices = tokenizer.text_to_sequence(text_left)
            polarity = int(polarity)+1
            dependency_dist = [float(d) for d in dist_lines[cnt*2+1].split()]
            
            cnt += 1
            # print(text_left, _, text_right)
            # print(aspect)
            # print(text_indices)
            # print(dependency_dist, cnt*2+1)

            data = {
                'text' : (text_left, _, text_right),
                'full_text' : (text_left, str(aspect), text_right),
                'text_indices': text_indices,
                'aspect_indices': aspect_indices,
                'left_indices': left_indices,
                'polarity': polarity,
                'dependency_dist': dependency_dist
            }

            all_data.append(data)
        return all_data

    def __init__(self, dataset='laptop', embed_dim=768):
        print("preparing {0} dataset...".format(dataset))
        fname = {
            'restaurant': {
                'train': './datasets/semeval14/Restaurants_Train.xml.seg',
                'test': './datasets/semeval14/Restaurants_Test_Gold.xml.seg'
            },
            'laptop': {
                'train': './datasets/semeval14/Laptops_Train.xml.seg',
                'test': './datasets/semeval14/Laptops_Test_Gold.xml.seg'
            },
            'restaurant16': {
                'train': './datasets/semeval16/restaurant_2016_training_coba_coba.xml.seg',
                'test': './datasets/semeval16/restaurant_2016_testing_gold_coba_coba.xml.seg'
            },
        }
        
                
        tokenizer = Tokenizer()
        data_raw = list(ABSADataset(ABSADatesetReader.__read_data__(fname[dataset]['train'], tokenizer)))
        
        self.train_data = ABSADataset(ABSADatesetReader.__read_data__(fname[dataset]['train'], tokenizer))
        self.test_data = ABSADataset(ABSADatesetReader.__read_data__(fname[dataset]['test'], tokenizer))

        text = ABSADatesetReader.__read_text__([fname[dataset]['train'], fname[dataset]['test']])

        if os.path.exists(dataset+'_word2idx.pkl'):
            print("loading {0} tokenizer...".format(dataset))
            with open(dataset+'_word2idx.pkl', 'rb') as f:
                word2idx = pickle.load(f)
                tokenizer = Tokenizer(word2idx=word2idx)
        else:
            tokenizer = Tokenizer()
            tokenizer.fit_on_text(text)
            with open(dataset+'_word2idx.pkl', 'wb') as f:
                pickle.dump(tokenizer.word2idx, f)


        # self.embedding_matrix = build_embedding_matrix(tokenizer.word2idx, embed_dim, dataset)
        self.embedding_matrix = build_embedding_matrix_bert(data_raw, 768, dataset)

        self.train_data = ABSADataset(ABSADatesetReader.__read_data__(fname[dataset]['train'], tokenizer))
        self.test_data = ABSADataset(ABSADatesetReader.__read_data__(fname[dataset]['test'], tokenizer))
