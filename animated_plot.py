import datetime as dt
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import random


expensive = True

if expensive == True:
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    xs = []
    ys = []
    sampling_time = 1000

    def animate(i, xs, ys):
        ys.append(random.randint(0,9))
        xs.append(dt.datetime.now().strftime('%H:%M:%S.%f'))
        xs = xs[-10:]
        ys = ys[-10:]

        ax.clear()
        ax.plot(xs, ys)

        plt.xticks(rotation=45, ha='right')
        plt.subplots_adjust(bottom=0.30)
        plt.title('Temperature data')
        plt.ylabel('Temperature (deg C)')

    ani = animation.FuncAnimation(fig, animate, fargs=(xs, ys), interval=sampling_time)
    plt.show()

else:
    x_len = 200       
    y_range = [10, 40] 
    fig = plt.figure()
    ax = fig.add_subplot(1, 2, 1)
    xs = []
    ys = []
    xs = range(0, 200)
    ys = [0,0]*x_len
    ax.set_ylim(y_range)
    line, = ax.plot(xs, ys)

    plt.title('Temperature')
    plt.xlabel('-')
    plt.ylabel('Temperature (deg C)')

    def animate_cheap(i, ys):
        ys.append(random.randint(20,30))
        ys = ys[-x_len:]
        line.set_ydata(ys)
        return line,

    ani = animation.FuncAnimation(fig,animate_cheap,fargs=(ys,),interval=50,blit=True)
    plt.show()