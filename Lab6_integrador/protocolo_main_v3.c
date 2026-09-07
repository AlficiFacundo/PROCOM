#include <stdio.h>
#include <string.h>
#include "xparameters.h"
#include "xil_types.h"
#include "xil_cache.h"
#include "xgpio.h"
#include "platform.h"
#include "xuartlite.h"

#define PORT_IN	 		XPAR_AXI_GPIO_0_BASEADDR
#define PORT_OUT 		XPAR_AXI_GPIO_0_BASEADDR
#define DEV_READ_SW     0x04
#define DEV_RF_WRITE    0x10   
#define DEV_RF_READ     0x11   

// Comandos del Register File
#define CMD_RD_SEL      0x08

// Codigos de o_rd_sel
#define RD_SWITCHES     0x0A

#define DATA_BUF_MAX 64

XGpio GpioOutput;
XGpio GpioInput;
XUartLite uart_module;

typedef struct {
    u8  is_long;
    u8  device;
    u16 size;
} Header;

static void read_bytes(u8 *buf, int n){
    int i=0;
    //Polling de recepción de cada Byte enviado a traves del uart.(XUartLite_Recv es no bloqueante, es decir que no espera
    // a que se reciba el byte, simplemente se fija lo que hay y lo toma.) 
    while(i<n){
        unsigned int recv = XUartLite_Recv(&uart_module, &buf[i], (unsigned int) 1);
        if(recv>0){
            i++;
        }
    }
}

static void send_bytes(u8 *buf, int n){
    //Mira la flag para saber si ya está enviando algo ---> True : Bucle vacío.
    while(XUartLite_IsSending(&uart_module)){}
    XUartLite_Send(&uart_module, buf, n);
}

static int read_header(Header *h){
    // Lee la cabecera resincronizando byte a byte: si el primer byte no
    // matchea el patron 101, se descarta de a uno (no de a 4), para poder
    // recuperarse solo ante un byte perdido o de mas en la linea.
    u8 b[4];
    read_bytes(&b[0],1);

    if(((b[0]>>5)&0x07) != 0x05){
        return -1; //Si no es 101, return -1 para indicar solapamiento de transmisiones.
    }

    read_bytes(&b[1],3); //resto de la cabecera, ya alineados

    h->is_long = (b[0]>>4)&0x01;
    h->device  = b[3];

    if(h->is_long){
        h->size = ((u16)b[1]<<8) | b[2]; //total de large
    } else {
        h->size = b[0]&0x0F; //total de short
    }
    return 0;
}


static int read_trailer(Header *h){
    // Lee el byte de fin de trama (010 + L/S + S.Size) y lo valida contra
    // los mismos campos leidos en la cabecera. Devuelve -1 si hay diferencias.
    u8 t;
    read_bytes(&t,1);

    if(((t>>5)&0x07) != 0x02){
        return -1; //Si no es 010, return -1 para indicar error de transmisión.
    }

    u8 t_is_long = (t>>4)&0x01;
    if(t_is_long != h->is_long){
        return -1; // Si hay una diferencia del L/S, se devuelve error de transmisión
    }

    if(!h->is_long){
        u8 t_size = t & 0x0F;
        if(t_size != (h->size & 0x0F)){
            return -1; // De igual manera, si difieren los L/S, error de transmisión.
        }
    }
    return 0;
}

static void build_and_send_frame(u8 device, u8 *data, u16 size){
    // Arma y envia una trama completa (cabecera + data + fin de trama)
    u8 hdr[4]; //header
    u8 trl[1]; //trailer o cola
    u8 is_long = (size>15); // longitud de trama

    if(is_long){
        //construcción para trama larga 
        hdr[0] = (0x05<<5) | (0x01<<4); //10110
        hdr[1] = (u8)(size>>8); //sizeH
        hdr[2] = (u8)(size&0xFF); //sizeL
        trl[0] = (0x02<<5) | (0x01<<4); //01010
    } else {
        //construcción para trama corta 
        hdr[0] = (0x05<<5) | (size&0x0F); //1010+size
        hdr[1] = 0x00; //sizeL = 0
        hdr[2] = 0x00; //sizeH = 0
        trl[0] = (0x02<<5) | (size&0x0F); //0100+size
    }
    hdr[3] = device;

    //enviar header, luego data y por ultimo trailer.
    send_bytes(hdr,4); 
    if(size>0){
        send_bytes(data,size); 
    }
    send_bytes(trl,1);
}

static void rf_delay(void){
    // Espera breve entre escrituras del GPIO para garantizar que el pulso
    // de "enable" dure lo suficiente para ser visto en el dominio de
    // clock del RF (clockdsp), que puede ser mucho mas lento que el del uP.
    volatile int i;
    for(i=0; i<2000; i++){}
}

static void rf_strobe(u8 command, u32 field23){
    // Escribe un registro del RF: valor(E=0) -> valor(E=1) -> valor(E=0)
    u32 base = ((u32)command<<24) | (field23 & 0x7FFFFF);
    u32 en   = base | (1u<<23);

    XGpio_DiscreteWrite(&GpioOutput,1, base);
    rf_delay();
    XGpio_DiscreteWrite(&GpioOutput,1, en);
    rf_delay();
    XGpio_DiscreteWrite(&GpioOutput,1, base);
    rf_delay();
}

int main()
{
    init_platform();
    int Status;
    XUartLite_Initialize(&uart_module, 0);

    Status = XGpio_Initialize(&GpioInput, PORT_IN);
    if(Status!=XST_SUCCESS){ return XST_FAILURE; }
    Status = XGpio_Initialize(&GpioOutput, PORT_OUT);
    if(Status!=XST_SUCCESS){ return XST_FAILURE; }

    XGpio_SetDataDirection(&GpioOutput,1,0x00000000);
    XGpio_SetDataDirection(&GpioInput,1,0xFFFFFFFF);
    while(1){
        Header h;
        if(read_header(&h)!=0){
            continue; //esperar trama, vuelve.
        }

        u8 data[DATA_BUF_MAX];
        if(h.size>0 && h.size<=DATA_BUF_MAX){
            read_bytes(data,h.size); //limita la capacidad de data.
        }

        if(read_trailer(&h)!=0){
            continue; // si el trailer no matchea con la cabecera, se descarta la trama
        }

        switch(h.device){
            case DEV_READ_SW: {
                // El GPIO de entrada esta multiplexado por rd_sel del RF:
                // hay que seleccionar los switches antes de leer.
                rf_strobe(CMD_RD_SEL, RD_SWITCHES);
                u32 sw = XGpio_DiscreteRead(&GpioInput,1);
                u8 resp = (u8)(sw & 0x0F);
                build_and_send_frame(DEV_READ_SW,&resp,1);
                break;
            }
            case DEV_RF_WRITE: {
                // data[0]=command, data[1..3]=data[22:0] (MSB primero, bit alto de data[1] sin usar)
                if(h.size==4){
                    u8  cmd   = data[0];
                    u32 field = ((u32)(data[1]&0x7F)<<16) | ((u32)data[2]<<8) | data[3];
                    rf_strobe(cmd, field);
                }
                break;
            }
            case DEV_RF_READ: {
                // data[0]=rd_sel -> selecciona el registro, luego lee el GPIO de entrada
                if(h.size==1){
                    u8 rd_sel = data[0];
                    rf_strobe(CMD_RD_SEL, (u32)rd_sel);

                    u32 val = XGpio_DiscreteRead(&GpioInput,1);
                    u8 resp[4] = { (u8)(val>>24), (u8)(val>>16), (u8)(val>>8), (u8)val };
                    build_and_send_frame(DEV_RF_READ, resp, 4);
                }
                break;
            }
            default:
                break;
        }
    }
    cleanup_platform();
    return 0;
}