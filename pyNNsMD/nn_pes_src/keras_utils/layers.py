"""
Keras layers for feature and model predictions around MLP.

@author: Patrick
"""
import numpy as np
import tensorflow as tf
import tensorflow.keras as ks

from pyNNsMD.nn_pes_src.keras_utils.activ import leaky_softplus,shifted_softplus

    
class ConstLayerNormalization(ks.layers.Layer):
    """
    Layer normalization with constant scaling of input.
    
    Note that this sould be replaced with keras normalization layer where trainable could be altered.
    The standardization is done via 'std' and 'mean' tf.variable and uses not very flexible broadcasting.

    """
    
    def __init__(self, axis=-1 , **kwargs):
        """
        Init the layer.

        Args:
            axis (int,list, optional): Which axis match the input on build. Defaults to -1.
            **kwargs

        """
        super(ConstLayerNormalization, self).__init__(**kwargs)          
        self.axis = axis
    def build(self, input_shape):
        """
        Build the layer.

        Args:
            input_shape (list): Shape of Input.

        Raises:
            TypeError: Axis argument is not valud.

        """
        super(ConstLayerNormalization, self).build(input_shape) 
        outshape = [1]*len(input_shape)
        if(isinstance(self.axis, int) == True):
            outshape[self.axis] = input_shape[self.axis]
        elif(isinstance(self.axis, list) == True or isinstance(self.axis, tuple) == True ):
            for i in self.axis:
                outshape[i] = input_shape[i]
        else:
            raise TypeError("Invalid axis argument")
        self.wmean = self.add_weight(
            'mean',
            shape=outshape,
            initializer=tf.keras.initializers.Zeros(),
            dtype=self.dtype,
            trainable=False)         
        self.wstd = self.add_weight(
            'std',
            shape=outshape,
            initializer= tf.keras.initializers.Ones(),
            dtype=self.dtype,
            trainable=False)
    def call(self, inputs):
        """
        Forward pass of the layer. Call().

        Args:
            inputs (tf.tensor): Tensor to scale.

        Returns:
            out (tf.tensor): (inputs-mean)/std

        """
        out = (inputs-self.wmean)/(self.wstd + tf.keras.backend.epsilon())
        return out 
    def get_config(self):
        """
        Config for the layer.

        Returns:
            config (dict): super.config with updated axis parameter.

        """
        config = super(ConstLayerNormalization, self).get_config()
        config.update({"axs": self.axis})
        return config 




class MLP(ks.layers.Layer):
    def __init__(self,
                 dense_units,
                 dense_depth = 1,
                 dense_bias = True,
                 dense_bias_last = True,
                 dense_activ = None,
                 dense_activ_last = None,
                 dense_activity_regularizer=None,
                 dense_kernel_regularizer=None,
                 dense_bias_regularizer=None,
                 dropout_use = False,
                 dropout_dropout = 0,
                 **kwargs):
        super(MLP, self).__init__(**kwargs) 
        self.dense_units = dense_units
        self.dense_depth = dense_depth 
        self.dense_bias =  dense_bias  
        self.dense_bias_last = dense_bias_last 
        self.dense_activ_serialize = dense_activ
        self.dense_activ = ks.activations.deserialize(dense_activ,custom_objects={'leaky_softplus':leaky_softplus,'shifted_softplus':shifted_softplus})
        self.dense_activ_last_serialize = dense_activ_last
        self.dense_activ_last = ks.activations.deserialize(dense_activ_last,custom_objects={'leaky_softplus':leaky_softplus,'shifted_softplus':shifted_softplus})
        self.dense_activity_regularizer = ks.regularizers.get(dense_activity_regularizer)
        self.dense_kernel_regularizer = ks.regularizers.get(dense_kernel_regularizer)
        self.dense_bias_regularizer = ks.regularizers.get(dense_bias_regularizer)
        self.dropout_use = dropout_use
        self.dropout_dropout = dropout_dropout
        
        self.mlp_dense_activ = [ks.layers.Dense(
                                self.dense_units,
                                use_bias=self.dense_bias,
                                activation=self.dense_activ,
                                name=self.name+'_dense_'+str(i),
                                activity_regularizer= self.dense_activity_regularizer,
                                kernel_regularizer=self.dense_kernel_regularizer,
                                bias_regularizer=self.dense_bias_regularizer
                                ) for i in range(self.dense_depth-1)]
        self.mlp_dense_last =  ks.layers.Dense(
                                self.dense_units,
                                use_bias=self.dense_bias_last,
                                activation=self.dense_activ_last,
                                name= self.name + '_last',
                                activity_regularizer= self.dense_activity_regularizer,
                                kernel_regularizer=self.dense_kernel_regularizer,
                                bias_regularizer=self.dense_bias_regularizer
                                )
        if(self.dropout_use == True):
            self.mlp_dropout =  ks.layers.Dropout(self.dropout_dropout,name=self.name + '_dropout')
    def build(self, input_shape):
        super(MLP, self).build(input_shape)          
    def call(self, inputs,training=False):
        x = inputs
        for i in range(self.dense_depth-1):
            x = self.mlp_dense_activ[i](x)
            if(self.dropout_use == True):
                x = self.mlp_dropout(x,training=training)
        x = self.mlp_dense_last(x)
        out = x
        return out
    def get_config(self):
        config = super(MLP, self).get_config()
        config.update({"dense_units": self.dense_units,
                       'dense_depth': self.dense_depth,
                       'dense_bias': self.dense_bias,
                       'dense_bias_last': self.dense_bias_last,
                       'dense_activ' : self.dense_activ_serialize,
                       'dense_activ_last' : self.dense_activ_last_serialize,
                       'dense_activity_regularizer': ks.regularizers.serialize(self.dense_activity_regularizer),
                       'dense_kernel_regularizer': ks.regularizers.serialize(self.dense_kernel_regularizer),
                       'dense_bias_regularizer': ks.regularizers.serialize(self.dense_bias_regularizer),
                       'dropout_use': self.dropout_use,
                       'dropout_dropout': self.dropout_dropout
                       })
        return config


class InverseDistance(ks.layers.Layer):
    def __init__(self , **kwargs):
        super(InverseDistance, self).__init__(**kwargs)  
        #self.dinv_mean = dinv_mean
        #self.dinv_std = dinv_std
    def build(self, input_shape):
        super(InverseDistance, self).build(input_shape)          
    def call(self, inputs):
        coords = inputs #(batch,N,3)
        #Compute square dinstance matrix
        ins_int = ks.backend.int_shape(coords)
        ins = ks.backend.shape(coords)
        a = ks.backend.expand_dims(coords ,axis = 1)
        b = ks.backend.expand_dims(coords ,axis = 2)
        c = b-a #(batch,N,N,3)
        d = ks.backend.sum(ks.backend.square(c),axis = -1) #squared distance without sqrt for derivative
        #Compute Mask for lower tri
        ind1 = ks.backend.expand_dims(ks.backend.arange(0,ins_int[1]),axis=1)
        ind2 = ks.backend.expand_dims(ks.backend.arange(0,ins_int[1]),axis=0)
        mask = ks.backend.less(ind1,ind2)
        mask = ks.backend.expand_dims(mask,axis=0)
        mask = ks.backend.tile(mask,(ins[0],1,1)) #(batch,N,N)
        #Apply Mask and reshape 
        d = d[mask]
        d = ks.backend.reshape(d,(ins[0],ins_int[1]*(ins_int[1]-1)//2)) # Not pretty
        d = ks.backend.sqrt(d) #Now the sqrt is okay
        out = 1/d #Now inverse should also be okay
        #out = (out - self.dinv_mean )/self.dinv_std #standardize with fixed values.
        return out 


class Angles(ks.layers.Layer):
    def __init__(self, angle_list, **kwargs):
        super(Angles, self).__init__(**kwargs)  
        self.angle_list = angle_list
        self.angle_list_tf = tf.constant(np.array(angle_list))
    def build(self, input_shape):
        super(Angles, self).build(input_shape)          
    def call(self, inputs):
        cordbatch  = inputs
        angbatch  = tf.repeat(ks.backend.expand_dims(self.angle_list_tf,axis=0) , ks.backend.shape(cordbatch)[0], axis=0)
        vcords1 = tf.gather(cordbatch, angbatch[:,:,1],axis=1,batch_dims=1)
        vcords2a = tf.gather(cordbatch, angbatch[:,:,0],axis=1,batch_dims=1)
        vcords2b = tf.gather(cordbatch, angbatch[:,:,2],axis=1,batch_dims=1)
        vec1=vcords2a-vcords1
        vec2=vcords2b-vcords1
        norm_vec1 = ks.backend.sqrt(ks.backend.sum(vec1*vec1,axis=-1))
        norm_vec2 = ks.backend.sqrt(ks.backend.sum(vec2*vec2,axis=-1))
        angle_cos = ks.backend.sum(vec1*vec2,axis=-1)/ norm_vec1 /norm_vec2
        angs_rad = tf.math.acos(angle_cos)
        return angs_rad
    def get_config(self):
        config = super(Angles, self).get_config()
        config.update({"angle_list": self.angle_list})
        return config


class Dihydral(ks.layers.Layer):
    def __init__(self ,angle_list, **kwargs):
        super(Dihydral, self).__init__(**kwargs)  
        self.angle_list = angle_list
        self.angle_list_tf = tf.constant(np.array(angle_list))
    def build(self, input_shape):
        super(Dihydral, self).build(input_shape)          
    def call(self, inputs):
        #implementation from
        #https://en.wikipedia.org/wiki/Dihedral_angle
        cordbatch = inputs
        indexbatch  = tf.repeat(ks.backend.expand_dims(self.angle_list_tf,axis=0) , ks.backend.shape(cordbatch)[0], axis=0)
        p1 = tf.gather(cordbatch, indexbatch[:,:,0],axis=1,batch_dims=1)
        p2 = tf.gather(cordbatch, indexbatch[:,:,1],axis=1,batch_dims=1)
        p3 = tf.gather(cordbatch, indexbatch[:,:,2],axis=1,batch_dims=1)
        p4 = tf.gather(cordbatch, indexbatch[:,:,3],axis=1,batch_dims=1)
        b1 = p1-p2  
        b2 = p2-p3
        b3 = p4-p3
        arg1 = ks.backend.sum(b2*tf.linalg.cross(tf.linalg.cross(b3,b2),tf.linalg.cross(b1,b2)),axis=-1)
        arg2 = ks.backend.sqrt(ks.backend.sum(b2*b2,axis=-1))*ks.backend.sum(tf.linalg.cross(b1,b2)*tf.linalg.cross(b3,b2),axis=-1)
        angs_rad = tf.math.atan2(arg1,arg2) 
        return angs_rad
    def get_config(self):
        config = super(Dihydral, self).get_config()
        config.update({"angle_list": self.angle_list})
        return config



class FeatureGeometric(ks.layers.Layer):
    """
    Feautre representation consisting of inverse distances, angles and dihydral angles.
    
    Uses InverseDistance, Angle, Dihydral if input index is not empty.
    
    """
    
    def __init__(self ,
                 invd_index = [],
                 angle_index = [],
                 dihyd_index = [],
                 **kwargs):
        """
        Init of the layer.

        Args:
            invd_index (list, optional): Index of atoms to calculate inverse distances. Defaults to [].
            angle_index (list, optional): Index of atoms to calculate angles between. Defaults to [].
            dihyd_index (list, optional): Index of atoms to calculate dihyd between. Defaults to [].
            **kwargs

        """
        super(FeatureGeometric, self).__init__(**kwargs)
        use_invdist = invd_index != []
        use_bond_angles = angle_index != []
        self.angle_index = angle_index 
        use_dihyd_angles = dihyd_index != []
        self.dihyd_index = dihyd_index
        
        self.use_dihyd_angles = use_dihyd_angles
        self.use_bond_angles = use_bond_angles
        self.use_invdist = use_invdist

        if(self.use_invdist==True):        
            self.invd_layer = InverseDistance()
        if(self.use_bond_angles==True):
            self.ang_layer = Angles(angle_list=angle_index)
            self.concat_ang = ks.layers.Concatenate(axis=-1)
        if(self.use_dihyd_angles==True):
            self.dih_layer = Dihydral(angle_list=dihyd_index)
            self.concat_dih = ks.layers.Concatenate(axis=-1)
        self.flat_layer = ks.layers.Flatten(name='feat_flat')
    def build(self, input_shape):
        """
        Build model. Passes to base class.

        Args:
            input_shape (list): Input shape.

        """
        super(FeatureGeometric, self).build(input_shape)
    def call(self, inputs):
        """
        Forward pass of the layer. Call().

        Args:
            inputs (tf.tensor): Coordinates of shape (batch,N,3).

        Returns:
            out (tf.tensor): Feature description of shape (batch,M).

        """
        x = inputs
        if(self.use_invdist==True):
            feat = self.invd_layer(x)
        if(self.use_bond_angles==True):
            if(self.use_invdist==False):
                feat = self.ang_layer(x)
            else:
                angs = self.ang_layer(x)
                feat = self.concat_ang([feat,angs],axis=-1)
        if(self.use_dihyd_angles==True):
            if(self.use_invdist==False and self.use_bond_angles==False):
                feat = self.dih_layer(x)
            else:
                dih = self.dih_layer(x)
                feat = self.concat_dih([feat,dih],axis=-1)
    
        feat_flat = self.flat_layer(feat)
        out = feat_flat
        return out 
    

class EnergyGradient(ks.layers.Layer):
    def __init__(self, mult_states = 1, **kwargs):
        super(EnergyGradient, self).__init__(**kwargs)          
        self.mult_states = mult_states
    def build(self, input_shape):
        super(EnergyGradient, self).build(input_shape)          
    def call(self, inputs):
        energy,coords = inputs
        out = [ks.backend.expand_dims(ks.backend.gradients(energy[:,i],coords)[0],axis=1) for i in range(self.mult_states)]
        out = ks.backend.concatenate(out,axis=1)   
        return out
    def get_config(self):
        config = super(EnergyGradient, self).get_config()
        config.update({"mult_states": self.mult_states})
        return config


class NACGradient(ks.layers.Layer):
    def __init__(self, mult_states = 1, atoms = 1, **kwargs):
        super(NACGradient, self).__init__(**kwargs)          
        self.mult_states = mult_states
        self.atoms=atoms
    def build(self, input_shape):
        super(NACGradient, self).build(input_shape)          
    def call(self, inputs):
        energy,coords = inputs
        out = ks.backend.concatenate([ks.backend.expand_dims(ks.backend.gradients(energy[:,i],coords)[0],axis=1) for i in range(self.mult_states*self.atoms)],axis=1)
        out = ks.backend.reshape(out,(ks.backend.shape(coords)[0],self.mult_states,self.atoms,self.atoms,3))
        out = ks.backend.concatenate([ks.backend.expand_dims(out[:,:,i,i,:],axis=2) for i in range(self.atoms)],axis=2)
        return out
    def get_config(self):
        config = super(NACGradient, self).get_config()
        config.update({"mult_states": self.mult_states,'atoms': self.atoms})
        return config 
    
    
class EmptyGradient(ks.layers.Layer):
    def __init__(self, mult_states = 1, atoms = 1, **kwargs):
        super(EmptyGradient, self).__init__(**kwargs)          
        self.mult_states = mult_states
        self.atoms=atoms
    def build(self, input_shape):
        super(EmptyGradient, self).build(input_shape)          
    def call(self, inputs):
        pot = inputs
        out = tf.zeros((ks.backend.shape(pot)[0],self.mult_states,self.atoms,3))
        return out
    def get_config(self):
        config = super(EmptyGradient, self).get_config()
        config.update({"mult_states": self.mult_states,'atoms': self.atoms})
        return config 
    

class PropagateEnergyGradient(ks.layers.Layer):
    def __init__(self,mult_states = 1 ,**kwargs):
        super(PropagateEnergyGradient, self).__init__(**kwargs) 
        self.mult_states = mult_states         
    def build(self, input_shape):
        super(PropagateEnergyGradient, self).build(input_shape)          
    def call(self, inputs):
        grads,grads2 = inputs
        out = ks.backend.batch_dot(grads,grads2,axes=(2,1))
        return out
    def get_config(self):
        config = super(PropagateEnergyGradient, self).get_config()
        config.update({"mult_states": self.mult_states})
        return config 


class PropagateNACGradient(ks.layers.Layer):
    def __init__(self,mult_states = 1,atoms=1 ,**kwargs):
        super(PropagateNACGradient, self).__init__(**kwargs) 
        self.mult_states = mult_states 
        self.atoms = atoms        
    def build(self, input_shape):
        super(PropagateNACGradient, self).build(input_shape)          
    def call(self, inputs):
        grads,grads2 = inputs
        out = ks.backend.batch_dot(grads,grads2,axes=(3,1))
        out = ks.backend.concatenate([ks.backend.expand_dims(out[:,:,i,i,:],axis=2) for i in range(self.atoms)],axis=2)
        return out
    def get_config(self):
        config = super(PropagateNACGradient, self).get_config()
        config.update({"mult_states": self.mult_states,'atoms': self.atoms})
        return config 

class PropagateNACGradient2(ks.layers.Layer):
    def __init__(self,axis=(2,1),**kwargs):
        super(PropagateNACGradient2, self).__init__(**kwargs) 
        self.axis = axis
    def build(self, input_shape):
        super(PropagateNACGradient2, self).build(input_shape)          
    def call(self, inputs):
        grads,grads2 = inputs
        out = ks.backend.batch_dot(grads,grads2,axes=self.axis)        
        return out
    def get_config(self):
        config = super(PropagateNACGradient2, self).get_config()
        config.update({"axis": self.axis})
        return config 