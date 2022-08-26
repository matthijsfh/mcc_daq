#Python 3.x
import matplotlib.pyplot as plt
import pandas as pd
data = pd.read_csv('scan_data.csv')

display(data)


st_name=data[' Channel 0']


marks=data['Marks']

x=list(st_name)
y=list(marks)

plt.bar(x, y, color = 'g', width = 0.5, label = "Marks")
plt.xlabel('Names')
plt.ylabel('Marks')
plt.title('Marks of different students')
plt.legend()
plt.show()