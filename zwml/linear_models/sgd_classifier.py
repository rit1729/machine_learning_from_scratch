import numpy as np
import pandas as pd

class sgd_classifier:
    
    def __init__(self, n_iter=10, alpha=0.01, verbose=False, return_steps=False, fit_intercept=True, 
                 dynamic=False, loss='ols', epsilon=0.1, random_state=None):
        """
        Stochastic Gradient Descent Algorithm, with Logistic Regression cost function.
        ---
        KWargs:
        
        n_iter: number of epochs to run in while fitting to the data. Total number of steps
        will be n_iter*X.shape[0]. 
        
        alpha: The learning rate. Moderates the step size during the gradient descent algorithm.
        
        verbose: Whether to print out coefficient information during the epochs
        
        return_steps: If True, fit returns a list of the coefficients at each update step for diagnostics
        
        fit_intercept: If True, an extra coefficient is added with no associated feature to act as the
                       base prediction if all X are 0.
                       
        dynamic: If true, an annealing scedule is used to scale the learning rate. 
        """
        self.coef_ = None
        self.trained = False
        self.n_iter = n_iter
        self.alpha_ = alpha
        self.verbosity = verbose
        self._return_steps = return_steps
        self._fit_intercept = fit_intercept
        self._next_alpha_shift = 0.1 # Only used if dynamic=True
        self._dynamic = dynamic
        if random_state:
            np.random.seed(random_state)
        self._data_cols = None
        
    def update(self, x, error):
        """
        Calculating the change of the coeficients for SGD. This is the derivative of the cost 
        function. B_i = B_i - alpha * dJ/dB_i. If fit_intercept=True, a slightly different 
        value is used to update the intercept coefficient, since the associated feature is "1."
        ---
        Inputs:
        
        data_point: A single row of the feature matrix. Since this is Stochastic, batches are not allowed.
        
        error: The residual for the current data point, given the current coefficients. Prediction - True
        for the current datapoint and coefficients.
        """
        step = self.alpha_*error*x
        if self._fit_intercept:
            self.coef_[1:] = self.coef_[1:] - step
            self.coef_[0] = self.coef_[0] - self.alpha_ * error
        else:
            self.coef_ = self.coef_ - step
        
    def shuffle_data(self, X, y):
        """
        Given X and y, shuffle them together to get a new_X and new_y that maintain feature-target
        correlations. 
        ---
        Inputs:
        
        X: A numpy array of any shape
        y: A numpy array of any shape
        
        Both X and y must have the same first dimension length.
        
        Returns:
        X,y: two numpy arrays
        """
        assert len(X) == len(y)
        permute = np.random.permutation(len(y))
        return X[permute], y[permute]
        
    def pandas_to_numpy(self, x):
        """
        Checks if the input is a Dataframe or series, converts to numpy matrix for
        calculation purposes.
        ---
        Input: X (array, dataframe, or series)
        
        Output: X (array)
        """
        if type(x) == type(pd.DataFrame()) or type(x) == type(pd.Series()):
            return x.as_matrix()
        if type(x) == type(np.array([1,2])):
            return x
        return np.array(x) 
    
    def dynamic_learning_rate_check(self, epoch):
        """
        If dynamic=True, shrink the learning rate by a factor of 2 after every 10% of
        the total number of epochs. This should cause a more direct path to the global 
        minimum after the initial large steps.
        ---
        Inputs: epoch (int,float), the current iteration number. 
        """
        percent_of_epochs = float(epoch)/float(self.n_iter)
        if percent_of_epochs > self._next_alpha_shift:
            self._next_alpha_shift += 0.1
            self.alpha_ = self.alpha_/2
            
    def fit(self, X, y):
        """
        Actually trains the model. Given feature-target combinations, gradient descent is performed
        using the optimization stepping given in the 'update' function. At present, all epochs are 
        completed, as no tolerance is set. The learning rate is currently fixed.
        ---
        Inputs: 
            X (array, dataframe, series), The features to regress on using SGD
            y (array, series), Must be a 1D set of targets.
        Outputs:
            steps (optional): If return_steps=True, a list of the evolution of the coefficients is returned
        """
        X = self.pandas_to_numpy(X)
        y = self.pandas_to_numpy(y)
        if not self._data_cols:
            try: 
                self._data_cols = X.shape[1]
            except IndexError:
                self._data_cols = 1
        X = self.check_feature_shape(X)
        self._stdy = np.std(y)
        self.coef_ = self.init_coef(X)
        if self._return_steps:
            steps = []
            steps.append(np.copy(self.coef_))
        for epoch in range(self.n_iter):
            shuf_X, shuf_y = self.shuffle_data(X,y)
            if self.verbosity:
                print("Epoch ", epoch, ", Coeff: ", self.coef_)
            for data, true in zip(shuf_X,shuf_y):
                pred = self.predict_proba(data)
                error = pred - true
                self.update(data, error)
                if self._return_steps:
                    steps.append(np.copy(self.coef_))
            if self._dynamic:
                self.dynamic_learning_rate_check(epoch)
        if self._return_steps:
            return steps
            
    def init_coef(self, X):
        """
        Returns the initial starting values for the coefficients. At present, these are randomly
        set. If fit_intercept = True, an extra coefficient is generated. 
        ---
        Input: X, Feature matrix. Needed to decide how many coefficients to generate.
        """
        if self._fit_intercept:
            return np.random.rand(X.shape[1]+1)
        return np.random.rand(X.shape[1])

    def predict_proba(self, X):  
        """
        Returns a prediction for a new data set, using the model coefficients.
        ---
        Input: 
            X (dataframe, array): The new feature set. Must be the same number of columns
            as the initial training features. 
        Output:
            prediction (array): The dot product of the input data and the coeficients.
        """
        X = self.pandas_to_numpy(X)
        X = self.check_feature_shape(X)
        if not self.coef_.all():
            raise ValueError("Coefficients not defined, must fit() before predict().")
        if self._fit_intercept:
            return self.logit(np.dot(X,self.coef_[1:]) + self.coef_[0])
        
        return self.logit(np.dot(X,self.coef_))
    
    def predict(self, X, threshold=0.5):
        preds = self.predict_proba(X)
        preds = list(map(lambda x: 1 if x >= threshold else 0, preds))
        return np.array(preds)
    
    def check_feature_shape(self, X):
        """
        Helper function to make sure any new data conforms to the fit data shape
        ---
        In: numpy array, (unknown shape)
        Out: numpy array, shape: (rows, self.data_cols)"""
        return X.reshape(-1,self._data_cols)
    
    def logit(self, beta_x):
        denom = 1. - np.exp(-beta_x)
        val = 1./denom
        
        def handle_rounding(x):
            # handles rounding errors which cause slightly negative or slightly >1 values
            if x > 1:
                return 1
            elif x < 0:
                return 0
            else:
                return x
        vals = list(map(handle_rounding, val))
        return np.array(vals)
      
    def score(self, X, y):
        """
        Uses the predict method to measure the accuracy of the model.
        ---
        In: X (list or array), feature matrix; y (list or array) labels
        Out: accuracy (float)
        """
        pred = self.predict(X)
        correct = 0
        for i,j in zip(y,pred):
            if i == j:
                correct+=1
        return float(correct)/float(len(y))