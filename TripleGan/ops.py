import tensorflow as tf
from tensorflow.keras.layers import GlobalAveragePooling2D, Flatten, BatchNormalization
import numpy as np
import math
from tensorflow.keras.initializers import VarianceScaling

he_init = VarianceScaling()
# he_init = tf.truncated_normal_initializer(stddev=0.02)
"""
The weight norm is not implemented at this time.
"""

def weight_norm(x, output_dim) :
    input_dim = int(x.get_shape()[-1])
    g = tf.compat.v1.get_variable('g_scalar', shape=[output_dim], dtype=tf.float32, initializer=tf.compat.v1.ones_initializer(), use_resource = False)
    w = tf.compat.v1.get_variable('weight', shape=[input_dim, output_dim], dtype=tf.float32, initializer=he_init, use_resource = False )
    w_init = tf.nn.l2_normalize(w, axis=0) * g  # SAME dim=1

    return tf.compat.v1.variables_initializer(w_init)

def conv_layer(x, filter_size, kernel, stride=1, padding='SAME', wn=False, layer_name="conv"):
    with tf.compat.v1.name_scope(layer_name):
        if wn:
            w_init = weight_norm(x, filter_size)

            x = tf.compat.v1.layers.conv2d(inputs=x, filters=filter_size, kernel_size=kernel, kernel_initializer=w_init, strides=stride, padding=padding)
        else :
            x = tf.compat.v1.layers.conv2d(inputs=x, filters=filter_size, kernel_size=kernel, kernel_initializer=he_init, strides=stride, padding=padding)
        return x


def deconv_layer(x, filter_size, kernel, stride=1, padding='SAME', wn=False, layer_name='deconv'):
    with tf.compat.v1.name_scope(layer_name):
        if wn :
            w_init = weight_norm(x, filter_size)
            x = tf.compat.v1.layers.conv2d_transpose(inputs=x, filters=filter_size, kernel_size=kernel, kernel_initializer=w_init, strides=stride, padding=padding)
        else :
            x = tf.compat.v1.layers.conv2d_transpose(inputs=x, filters=filter_size, kernel_size=kernel, kernel_initializer=he_init, strides=stride, padding=padding)
        return x


def linear(x, unit, wn=False, layer_name='linear'):
    with tf.compat.v1.name_scope(layer_name):
        if wn :
            w_init = weight_norm(x, unit)
            x = tf.compat.v1.layers.dense(inputs=x, units=unit, kernel_initializer=w_init)
        else :
            x = tf.compat.v1.layers.dense(inputs=x, units=unit, kernel_initializer=he_init)
        return x


def nin(x, unit, wn=False, layer_name='nin'):
    # https://github.com/openai/weightnorm/blob/master/tensorflow/nn.py
    with tf.compat.v1.name_scope(layer_name):
        s = list(map(int, x.get_shape()))
        x = tf.reshape(x, [np.prod(s[:-1]), s[-1]])
        x = linear(x, unit, wn, layer_name)
        x = tf.reshape(x, s[:-1] + [unit])


        return x


def gaussian_noise_layer(x, std=0.15):
    noise = tf.random.normal(shape=tf.shape(input=x), mean=0.0, stddev=std, dtype=tf.float32)
    return x + noise

def Global_Average_Pooling(x):
    return GlobalAveragePooling2D()(x)


def max_pooling(x, kernel, stride):
    return tf.compat.v1.layers.max_pooling2d(x, pool_size=kernel, strides=stride, padding='VALID')


def flatten(x):
    return Flatten()(x)


def lrelu(x, leak=0.2, name="lrelu"):
    return tf.maximum(x, leak * x)


def sigmoid(x):
    return tf.nn.sigmoid(x)


def relu(x):
    return tf.nn.relu(x)


def tanh(x):
    return tf.nn.tanh(x)

def conv_concat(x, y):
    x_shapes = x.get_shape()
    y_shapes = y.get_shape()

    return concat([x, y * tf.ones([x_shapes[0], x_shapes[1], x_shapes[2], y_shapes[3]])], axis=3)


def concat(x, axis=1):
    return tf.concat(x, axis=axis)


def reshape(x, shape):
    return tf.reshape(x, shape=shape)


def batch_norm(x, is_training):
    return BatchNormalization()(x,
    
    training=is_training)

def instance_norm(x, is_training, scope):
    with tf.compat.v1.variable_scope(scope):
        epsilon = 1e-5
        mean, var = tf.nn.moments(x=x, axes=[1, 2], keepdims=True)
        scale = tf.compat.v1.get_variable('scale', [x.get_shape()[-1]],
                                initializer=tf.compat.v1.truncated_normal_initializer(mean=1.0, stddev=0.02))
        offset = tf.compat.v1.get_variable('offset', [x.get_shape()[-1]], initializer=tf.compat.v1.constant_initializer(0.0))
        out = scale * tf.compat.v1.div(x - mean, tf.sqrt(var + epsilon)) + offset

        return out

def dropout(x, rate, is_training):
    return tf.compat.v1.layers.dropout(inputs=x, rate=rate, training=is_training)

def rampup(epoch):
    if epoch < 80:
        p = max(0.0, float(epoch)) / float(80)
        p = 1.0 - p
        return math.exp(-p*p*5.0)
    else:
        return 1.0

def rampdown(epoch):
    if epoch >= (300 - 50):
        ep = (epoch - (300 - 50)) * 0.5
        return math.exp(-(ep * ep) / 50)
    else:
        return 1.0